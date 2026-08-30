from pathlib import Path

from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.rag.ingestion import ingest_artifact
from tests.conftest import (
    authenticated_csrf_headers,
    create_qualified_request,
    enable_real_llm,
    promote,
    real_embedding_provider,
    register,
)

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "app" / "agent_manifest" / "fixtures"
FIXTURE_MANIFEST = (FIXTURES_DIR / "legacy-code-skill.md").read_text(encoding="utf-8")
BUSINESS_RULES_FIXTURE_MANIFEST = (FIXTURES_DIR / "business-rules-skill.md").read_text(encoding="utf-8")

TECHNICIAN = {
    "name": "Tecnica FollowUp",
    "email": "tecnica.followup@example.com",
    "password": "StrongPassword!123",
}


def _seed_knowledge_base() -> None:
    with SessionLocal() as db:
        ingest_artifact(
            db,
            artifact_name="CreditLimitService.java",
            content=(
                "O limite de credito hoje eh sempre R$ 5000,00 fixo, sem considerar "
                "o segmento do cliente (varejo, atacado, corporativo)."
            ),
            language="java",
            embedding_provider=real_embedding_provider(),
            max_chars=1000,
            overlap=0,
        )
        db.commit()


def test_ask_follow_up_requires_prior_execution(client: TestClient) -> None:
    register(client, TECHNICIAN)
    promote(TECHNICIAN["email"], "TECHNICIAN")
    client.post(
        "/api/v1/agent-skills/import",
        json={"manifest_markdown": FIXTURE_MANIFEST},
        headers=authenticated_csrf_headers(client),
    )
    technical_request = create_qualified_request(client, requested_domains=["codigo_legado"])

    response = client.post(
        f"/api/v1/agent-skills/requests/{technical_request['id']}/ask",
        json={"question": "Isso afeta clientes corporativos tambem?"},
        headers=authenticated_csrf_headers(client),
    )
    assert response.status_code == 409


def test_ask_follow_up_broadcast_and_persists(client: TestClient, monkeypatch) -> None:
    _seed_knowledge_base()
    register(client, TECHNICIAN)
    promote(TECHNICIAN["email"], "TECHNICIAN")
    client.post(
        "/api/v1/agent-skills/import",
        json={"manifest_markdown": FIXTURE_MANIFEST},
        headers=authenticated_csrf_headers(client),
    )
    technical_request = create_qualified_request(client, requested_domains=["codigo_legado"])

    enable_real_llm(monkeypatch)
    execute_response = client.post(
        f"/api/v1/agent-skills/requests/{technical_request['id']}/execute",
        headers=authenticated_csrf_headers(client),
    )
    assert execute_response.status_code == 200

    ask_response = client.post(
        f"/api/v1/agent-skills/requests/{technical_request['id']}/ask",
        json={"question": "Isso afeta clientes do segmento corporativo tambem?"},
        headers=authenticated_csrf_headers(client),
    )
    assert ask_response.status_code == 200
    exchange = ask_response.json()
    assert exchange["sequence_number"] == 1
    assert exchange["target_domain"] is None
    assert len(exchange["results"]) == 1
    assert exchange["results"][0]["agente_emissor"]["dominio"] == "codigo_legado"
    assert "[codigo_legado]" in exchange["synthesis"]

    events_response = client.get(f"/api/v1/orchestrations/{technical_request['trace_id']}/events")
    event_types = [event["event_type"] for event in events_response.json()]
    assert "FOLLOW_UP_QUESTION_ASKED" in event_types
    assert "FOLLOW_UP_RESPONSE_RECEIVED" in event_types

    follow_ups_response = client.get(
        f"/api/v1/orchestrations/{technical_request['trace_id']}/follow-ups"
    )
    assert follow_ups_response.status_code == 200
    follow_ups = follow_ups_response.json()
    assert len(follow_ups) == 1
    assert follow_ups[0]["id"] == exchange["id"]


def test_ask_follow_up_targets_specific_domain(client: TestClient, monkeypatch) -> None:
    _seed_knowledge_base()
    register(client, TECHNICIAN)
    promote(TECHNICIAN["email"], "TECHNICIAN")
    for manifest in (FIXTURE_MANIFEST, BUSINESS_RULES_FIXTURE_MANIFEST):
        import_response = client.post(
            "/api/v1/agent-skills/import",
            json={"manifest_markdown": manifest},
            headers=authenticated_csrf_headers(client),
        )
        assert import_response.status_code == 201

    technical_request = create_qualified_request(
        client, requested_domains=["codigo_legado", "regras_negocio"]
    )

    enable_real_llm(monkeypatch)
    execute_response = client.post(
        f"/api/v1/agent-skills/requests/{technical_request['id']}/execute",
        headers=authenticated_csrf_headers(client),
    )
    assert execute_response.status_code == 200
    assert execute_response.json()["invocations_count"] == 2

    # No Agent Skill registered for this domain -> 409 before any real call.
    no_skill_response = client.post(
        f"/api/v1/agent-skills/requests/{technical_request['id']}/ask",
        json={"question": "E do ponto de vista de seguranca?", "target_domain": "seguranca_informacao"},
        headers=authenticated_csrf_headers(client),
    )
    assert no_skill_response.status_code == 409

    ask_response = client.post(
        f"/api/v1/agent-skills/requests/{technical_request['id']}/ask",
        json={
            "question": "Quais regras de negocio definem esse limite hoje?",
            "target_domain": "regras_negocio",
        },
        headers=authenticated_csrf_headers(client),
    )
    assert ask_response.status_code == 200
    exchange = ask_response.json()
    assert exchange["target_domain"] == "regras_negocio"
    assert len(exchange["results"]) == 1
    assert exchange["results"][0]["agente_emissor"]["dominio"] == "regras_negocio"
