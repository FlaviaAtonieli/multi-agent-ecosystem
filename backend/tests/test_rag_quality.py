from pathlib import Path

from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.rag.evaluation import (
    GROUND_TRUTH_BY_DOMAIN,
    RetrievalEvalCase,
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

FIXTURES_ROOT = Path(__file__).resolve().parent.parent / "app" / "rag" / "fixtures"
_LANGUAGE_BY_SUFFIX = {".java": "java", ".sql": "sql", ".md": "markdown"}
TOP_K = 3

# Regression bars, picked with real margin below the numbers actually measured
# on 2026-09-21 against the live OpenRouter embedding model with all four
# fixture domains co-indexed in the same knowledge base (harder than measuring
# each domain in isolation, since chunks from the other three domains are now
# real distractors) -- see
# docs/validation/evidence/2026-09-rag-multi-domain-quality-validation.md.
#
# Measured: Código Legado MRR=0.875 R@3=0.750 (n=8, first measured alone on
# 2026-08-30 with R@3=0.812; the co-indexed re-measurement is honestly lower
# because there are now real distractors, not a regression in the pipeline);
# Regras de Negócio MRR=1.000 R@3=1.000 (n=5); Arquitetura de Software
# MRR=0.900 R@3=0.900 (n=5); Segurança da Informação MRR=1.000 R@3=1.000 (n=5).
#
# Floors leave room for one flipped query without treating normal embedding
# variance as a regression: 1/8=0.125 for the 8-query domain, 1/5=0.20 for the
# three 5-query domains.
MIN_MEAN_RECIPROCAL_RANK_BY_DOMAIN: dict[str, float] = {
    "Código Legado": 0.75,
    "Regras de Negócio": 0.80,
    "Arquitetura de Software": 0.70,
    "Segurança da Informação": 0.80,
}
MIN_MEAN_RECALL_AT_K_BY_DOMAIN: dict[str, float] = {
    "Código Legado": 0.60,
    "Regras de Negócio": 0.80,
    "Arquitetura de Software": 0.70,
    "Segurança da Informação": 0.80,
}


def _seed_full_knowledge_base() -> None:
    """Indexes every fixture domain (legacy_billing, business_rules, architecture,
    security) into the same shared knowledge base -- mirrors production, where all
    four official Agent Skills' knowledge lives in one `knowledge_chunks` table with
    no domain-scoped filter (see app/rag/retriever.py). Co-indexing them here is what
    makes this a real test of discrimination, not just recall within a single topic."""
    embedding_provider = real_embedding_provider()
    with SessionLocal() as db:
        for domain_dir in sorted(FIXTURES_ROOT.iterdir()):
            if not domain_dir.is_dir():
                continue
            for path in sorted(domain_dir.glob("*")):
                if not path.is_file():
                    continue
                ingest_artifact(
                    db,
                    artifact_name=path.name,
                    content=path.read_text(encoding="utf-8"),
                    language=_LANGUAGE_BY_SUFFIX.get(path.suffix),
                    source_type=f"{domain_dir.name}_fixture",
                    embedding_provider=embedding_provider,
                )
        db.commit()


def _measure(
    retriever: InMemoryVectorRetriever, cases: list[RetrievalEvalCase]
) -> tuple[float, float, float]:
    reciprocal_ranks: list[float] = []
    precisions: list[float] = []
    recalls: list[float] = []

    for case in cases:
        results = retriever.retrieve(case.query, top_k=TOP_K)
        retrieved_artifacts = [chunk.artifact_name for chunk in results]

        p_at_k = precision_at_k(retrieved_artifacts, case.relevant_artifacts, TOP_K)
        r_at_k = recall_at_k(retrieved_artifacts, case.relevant_artifacts, TOP_K)
        rr = reciprocal_rank(retrieved_artifacts, case.relevant_artifacts)

        precisions.append(p_at_k)
        recalls.append(r_at_k)
        reciprocal_ranks.append(rr)
        print(f"  {case.query[:66]:<68} P@{TOP_K}={p_at_k:.2f}  R@{TOP_K}={r_at_k:.2f}  RR={rr:.2f}")

    n = len(cases)
    return sum(precisions) / n, sum(recalls) / n, sum(reciprocal_ranks) / n


def test_retrieval_quality_against_ground_truth(client: TestClient) -> None:
    """Measures retrieval quality (Precision@k, Recall@k, MRR) against a hand-labeled
    ground truth grounded in the real fixture content of all four Agent Skill domains
    -- not synthetic/random data. Addresses the Portfolio Directions "IA" track
    requirement of validating the model with an adequate technique (here: standard
    information-retrieval metrics), and stands as a repeatable regression check per
    domain, not just a one-off report."""
    _seed_full_knowledge_base()

    with SessionLocal() as db:
        retriever = InMemoryVectorRetriever(db, real_embedding_provider())

        for domain, cases in GROUND_TRUTH_BY_DOMAIN.items():
            print(f"\n=== Domínio: {domain} (n={len(cases)}) ===")
            mean_precision, mean_recall, mean_rr = _measure(retriever, cases)
            print(
                f"  Mean P@{TOP_K}={mean_precision:.3f}  Mean R@{TOP_K}={mean_recall:.3f}  "
                f"MRR={mean_rr:.3f}"
            )

            assert mean_rr >= MIN_MEAN_RECIPROCAL_RANK_BY_DOMAIN[domain], domain
            assert mean_recall >= MIN_MEAN_RECALL_AT_K_BY_DOMAIN[domain], domain


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
    _seed_full_knowledge_base()

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
