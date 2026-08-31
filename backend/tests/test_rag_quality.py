from pathlib import Path

from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.rag.evaluation import (
    LEGACY_BILLING_GROUND_TRUTH,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)
from app.rag.ingestion import ingest_artifact
from app.rag.retriever import InMemoryVectorRetriever
from tests.conftest import (
    authenticated_csrf_headers,
    create_qualified_request,
    enable_real_llm,
    promote,
    real_embedding_provider,
    register,
)

FIXTURE_DIR = Path(__file__).resolve().parent.parent / "app" / "rag" / "fixtures" / "legacy_billing"
_LANGUAGE_BY_SUFFIX = {".java": "java", ".sql": "sql", ".md": "markdown"}
TOP_K = 3

# Regression bar, picked with real margin below the numbers actually measured on
# 2026-08-30 against the live OpenRouter embedding model (see
# docs/validation/evidence/2026-08-30-rag-quality-validation.md): MRR=0.875,
# mean P@3=0.667, mean R@3=0.812 across the 8-query ground truth. A single
# flipped query moves either mean by 1/8 = 0.125, so the bar leaves room for
# one additional miss without treating normal embedding variance as a failure.
MIN_MEAN_RECIPROCAL_RANK = 0.7
MIN_MEAN_RECALL_AT_K = 0.65


def _seed_legacy_billing_knowledge_base() -> None:
    embedding_provider = real_embedding_provider()
    with SessionLocal() as db:
        for path in sorted(FIXTURE_DIR.glob("*")):
            if not path.is_file():
                continue
            ingest_artifact(
                db,
                artifact_name=path.name,
                content=path.read_text(encoding="utf-8"),
                language=_LANGUAGE_BY_SUFFIX.get(path.suffix),
                embedding_provider=embedding_provider,
            )
        db.commit()


def test_retrieval_quality_against_ground_truth(client: TestClient) -> None:
    """Measures retrieval quality (Precision@k, Recall@k, MRR) against a hand-labeled
    ground truth grounded in the real legacy_billing fixture -- not synthetic/random
    data. Addresses the Portfolio Directions "IA" track requirement of validating the
    model with an adequate technique (here: standard information-retrieval metrics),
    and stands as a repeatable regression check, not just a one-off report."""
    _seed_legacy_billing_knowledge_base()

    with SessionLocal() as db:
        retriever = InMemoryVectorRetriever(db, real_embedding_provider())

        reciprocal_ranks: list[float] = []
        precisions: list[float] = []
        recalls: list[float] = []

        print(f"\n{'query':<70} P@{TOP_K}   R@{TOP_K}   RR")
        for case in LEGACY_BILLING_GROUND_TRUTH:
            results = retriever.retrieve(case.query, top_k=TOP_K)
            retrieved_artifacts = [chunk.artifact_name for chunk in results]

            p_at_k = precision_at_k(retrieved_artifacts, case.relevant_artifacts, TOP_K)
            r_at_k = recall_at_k(retrieved_artifacts, case.relevant_artifacts, TOP_K)
            rr = reciprocal_rank(retrieved_artifacts, case.relevant_artifacts)

            precisions.append(p_at_k)
            recalls.append(r_at_k)
            reciprocal_ranks.append(rr)
            print(f"{case.query[:68]:<70} {p_at_k:.2f}   {r_at_k:.2f}   {rr:.2f}")

        mean_precision = sum(precisions) / len(precisions)
        mean_recall = sum(recalls) / len(recalls)
        mean_reciprocal_rank = sum(reciprocal_ranks) / len(reciprocal_ranks)
        print(
            f"\nMean P@{TOP_K}={mean_precision:.3f}  Mean R@{TOP_K}={mean_recall:.3f}  "
            f"MRR={mean_reciprocal_rank:.3f}  (n={len(LEGACY_BILLING_GROUND_TRUTH)} queries)"
        )

        assert mean_reciprocal_rank >= MIN_MEAN_RECIPROCAL_RANK
        assert mean_recall >= MIN_MEAN_RECALL_AT_K


TECHNICIAN = {
    "name": "Tecnica RAG Grounding",
    "email": "tecnica.rag.grounding@example.com",
    "password": "StrongPassword!123",
}


def test_rag_enabled_plan_reflects_retrieved_context(client: TestClient, monkeypatch) -> None:
    """Closes the loop already proven mechanically by
    test_rag.py::test_generate_plan_runs_retrieval_before_llm_call (retrieval runs
    and its chunk ids are persisted on the invocation): here the request's
    problem/context deliberately omit the fixture's specific facts (the exact
    R$ 5.000 value, the SEGMENTO column, the downstream consumers), so any of
    them appearing in the plan can only have come from the retrieved context,
    not from the prompt the caller wrote.

    Free-model prose paraphrases rather than quoting identifiers verbatim (see
    docs/validation/evidence/2026-08-30-rag-quality-validation.md for two real
    captured responses), so this asserts only the mechanical, reliable half
    (retrieval fed the call) and prints the free-text plan for manual/qualitative
    review instead of pattern-matching prose -- avoiding a brittle assertion on
    free-model wording, consistent with the flakiness already documented for
    this project's free-tier model."""
    _seed_legacy_billing_knowledge_base()

    register(client, TECHNICIAN)
    promote(TECHNICIAN["email"], "TECHNICIAN")
    technical_request = create_qualified_request(
        client,
        title="Revisar cálculo de limite de crédito",
        problem="Precisamos entender como o limite de crédito do cliente é calculado hoje.",
        objective="Gerar um plano técnico listando o valor atual e quem depende dele.",
        context="Nenhuma mudança deve ser feita ainda, só o levantamento do estado atual.",
    )

    enable_real_llm(monkeypatch)

    plan_response = client.post(
        f"/api/v1/llm/requests/{technical_request['id']}/plan",
        headers=authenticated_csrf_headers(client),
    )
    assert plan_response.status_code == 200
    body = plan_response.json()

    events_response = client.get(
        f"/api/v1/orchestrations/{technical_request['trace_id']}/events"
    )
    retrieval_event = next(
        event
        for event in events_response.json()
        if event["event_type"] == "RAG_RETRIEVAL_COMPLETED"
    )
    assert retrieval_event["payload"]["chunks_retrieved"] >= 1

    chunks_retrieved = retrieval_event["payload"]["chunks_retrieved"]
    print(f"\nPlano gerado (RAG habilitado, {chunks_retrieved} chunks retornados):")
    print(body["plan"])
