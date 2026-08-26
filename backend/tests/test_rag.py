from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.database import SessionLocal
from app.models import LLMInvocation, OrchestrationEvent, User
from app.rag.ingestion import chunk_text, ingest_artifact
from app.rag.providers.mock_embedding_provider import MockEmbeddingProvider
from app.rag.retriever import InMemoryVectorRetriever
from tests.conftest import csrf_headers

TECHNICIAN = {
    "name": "Tecnica RAG",
    "email": "tecnica.rag@example.com",
    "password": "StrongPassword!123",
}


def authenticated_csrf_headers(client: TestClient) -> dict[str, str]:
    token = client.cookies.get("agenthub_csrf")
    assert token
    return {"X-CSRF-Token": token}


def register_user(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json=TECHNICIAN,
        headers=csrf_headers(client),
    )
    assert response.status_code == 201


def promote_current_user_to_technician() -> str:
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == TECHNICIAN["email"]))
        assert user is not None
        user.role = "TECHNICIAN"
        db.commit()
        return user.id


def create_qualified_request(client: TestClient) -> dict:
    response = client.post(
        "/api/v1/requests",
        json={
            "title": "Avaliar impacto de limite de crédito por segmento",
            "problem": (
                "O limite de crédito é global e precisa considerar o segmento do cliente."
            ),
            "objective": "Gerar plano técnico sem executar alterações automaticamente.",
            "context": (
                "O sistema legado calcula o limite de crédito do cliente de forma fixa, "
                "sem considerar o segmento, e isso precisa mudar com segurança."
            ),
            "restrictions": ["Não executar tools", "Não publicar automaticamente"],
        },
        headers=authenticated_csrf_headers(client),
    )
    assert response.status_code == 201
    assert response.json()["status"] == "QUALIFIED"
    return response.json()


def test_chunk_text_produces_overlapping_windows() -> None:
    content = "a" * 1000
    windows = chunk_text(content, max_chars=300, overlap=50)

    assert len(windows) > 1
    for chunk, start, end in windows:
        assert len(chunk) == end - start
        assert end - start <= 300

    # Consecutive windows must overlap by the configured amount.
    first_end = windows[0][2]
    second_start = windows[1][1]
    assert first_end - second_start == 50


def test_chunk_text_handles_empty_content() -> None:
    assert chunk_text("   ", max_chars=100, overlap=10) == []


def test_ingest_artifact_persists_chunks_with_embeddings(client: TestClient) -> None:
    with SessionLocal() as db:
        chunks = ingest_artifact(
            db,
            artifact_name="CreditLimitService.java",
            content=(
                "O limite de credito hoje eh sempre R$ 5000,00 fixo, "
                "sem considerar o segmento do cliente." * 5
            ),
            language="java",
            embedding_provider=MockEmbeddingProvider(),
            max_chars=100,
            overlap=20,
        )
        db.commit()

        assert len(chunks) > 1
        for chunk in chunks:
            assert chunk.id
            assert chunk.embedding
            assert any(value != 0 for value in chunk.embedding)


def test_in_memory_retriever_ranks_relevant_chunk_first(client: TestClient) -> None:
    with SessionLocal() as db:
        embedding_provider = MockEmbeddingProvider()
        ingest_artifact(
            db,
            artifact_name="CreditLimitService.java",
            content="limite de credito segmento cliente varejo atacado corporativo",
            language="java",
            embedding_provider=embedding_provider,
            max_chars=1000,
            overlap=0,
        )
        ingest_artifact(
            db,
            artifact_name="LoggingUtils.java",
            content="rotina de logging assincrono para depuracao de performance",
            language="java",
            embedding_provider=embedding_provider,
            max_chars=1000,
            overlap=0,
        )
        db.commit()

        retriever = InMemoryVectorRetriever(db, embedding_provider)
        results = retriever.retrieve("qual o limite de credito por segmento do cliente", top_k=2)

        assert results
        assert results[0].artifact_name == "CreditLimitService.java"


def test_generate_plan_runs_retrieval_before_llm_call(client: TestClient, monkeypatch) -> None:
    with SessionLocal() as db:
        ingest_artifact(
            db,
            artifact_name="CreditLimitService.java",
            content=(
                "O limite de credito hoje eh sempre R$ 5000,00 fixo, sem considerar "
                "o segmento do cliente (varejo, atacado, corporativo)."
            ),
            language="java",
            embedding_provider=MockEmbeddingProvider(),
            max_chars=1000,
            overlap=0,
        )
        db.commit()

    from app.core.config import settings

    register_user(client)
    promote_current_user_to_technician()
    technical_request = create_qualified_request(client)

    monkeypatch.setattr(settings, "llm_enabled", True)
    monkeypatch.setattr(settings, "llm_provider", "mock")
    monkeypatch.setattr(settings, "llm_model", "gpt-5-mini")

    plan_response = client.post(
        f"/api/v1/llm/requests/{technical_request['id']}/plan",
        headers=authenticated_csrf_headers(client),
    )
    assert plan_response.status_code == 200
    llm_call_id = plan_response.json()["llm_call_id"]

    events_response = client.get(
        f"/api/v1/orchestrations/{technical_request['trace_id']}/events"
    )
    assert events_response.status_code == 200
    events = events_response.json()
    event_types = [event["event_type"] for event in events]

    assert "RAG_RETRIEVAL_COMPLETED" in event_types
    assert "LLM_INVOCATION_STARTED" in event_types
    assert event_types.index("RAG_RETRIEVAL_COMPLETED") < event_types.index("LLM_INVOCATION_STARTED")

    retrieval_event = next(e for e in events if e["event_type"] == "RAG_RETRIEVAL_COMPLETED")
    assert retrieval_event["payload"]["chunks_retrieved"] >= 1

    with SessionLocal() as db:
        invocation = db.scalar(
            select(LLMInvocation).where(LLMInvocation.llm_call_id == llm_call_id)
        )
        assert invocation is not None
        assert invocation.retrieved_chunk_ids
        assert len(invocation.retrieved_chunk_ids) >= 1

        orchestration_events = db.scalars(
            select(OrchestrationEvent)
            .where(OrchestrationEvent.technical_request_id == invocation.technical_request_id)
            .order_by(OrchestrationEvent.sequence_number)
        ).all()
        assert [e.event_type for e in orchestration_events].count("RAG_RETRIEVAL_COMPLETED") == 1


def test_rag_disabled_skips_retrieval(client: TestClient, monkeypatch) -> None:
    from app.core.config import settings

    register_user(client)
    promote_current_user_to_technician()
    technical_request = create_qualified_request(client)

    monkeypatch.setattr(settings, "llm_enabled", True)
    monkeypatch.setattr(settings, "llm_provider", "mock")
    monkeypatch.setattr(settings, "rag_enabled", False)

    plan_response = client.post(
        f"/api/v1/llm/requests/{technical_request['id']}/plan",
        headers=authenticated_csrf_headers(client),
    )
    assert plan_response.status_code == 200

    events_response = client.get(
        f"/api/v1/orchestrations/{technical_request['trace_id']}/events"
    )
    event_types = [event["event_type"] for event in events_response.json()]
    assert "RAG_RETRIEVAL_COMPLETED" in event_types

    retrieval_event = next(
        e for e in events_response.json() if e["event_type"] == "RAG_RETRIEVAL_COMPLETED"
    )
    assert retrieval_event["payload"]["chunks_retrieved"] == 0
