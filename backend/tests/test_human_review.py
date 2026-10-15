from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.conftest import (
    authenticated_csrf_headers,
    create_qualified_request,
    enable_real_llm,
    register,
)

FIXTURE_MANIFEST = (
    Path(__file__).resolve().parent.parent
    / "app"
    / "agent_manifest"
    / "fixtures"
    / "legacy-code-skill.md"
).read_text(encoding="utf-8")

TECHNICIAN = {
    "name": "Tecnica Revisao",
    "email": "tecnica.revisao@example.com",
    "password": "StrongPassword!123",
}
OUTSIDER = {
    "name": "Usuaria Externa",
    "email": "usuaria.externa@example.com",
    "password": "StrongPassword!123",
}


def _create_request_pending_review(client: TestClient, monkeypatch) -> dict:
    """Executes a skill with no knowledge base ingested: zero retrieved chunks
    forces BAIXO confidence in LegacyCodeSkillExecutor, so the Quality Gate
    rejects and flags requires_human_review — a deterministic way to land a
    request in VALIDATING without depending on LLM output variance."""
    register(client, TECHNICIAN)

    client.post(
        "/api/v1/agent-skills/import",
        json={"manifest_markdown": FIXTURE_MANIFEST},
        headers=authenticated_csrf_headers(client),
    )

    technical_request = create_qualified_request(client, requested_domains=["codigo_legado"])

    enable_real_llm(monkeypatch)

    execution_response = client.post(
        f"/api/v1/agent-skills/requests/{technical_request['id']}/execute",
        headers=authenticated_csrf_headers(client),
    )
    assert execution_response.status_code == 200
    assert execution_response.json()["verdict"]["requires_human_review"] is True

    detail_response = client.get(f"/api/v1/requests/{technical_request['id']}")
    assert detail_response.json()["status"] == "VALIDATING"
    return technical_request


@pytest.mark.llm
def test_requester_approves_pending_request(client: TestClient, monkeypatch) -> None:
    technical_request = _create_request_pending_review(client, monkeypatch)

    response = client.post(
        f"/api/v1/requests/{technical_request['id']}/review",
        json={"decision": "approve", "notes": "Evidência suficiente apesar da confiança baixa."},
        headers=authenticated_csrf_headers(client),
    )
    assert response.status_code == 200
    assert response.json()["status"] == "COMPLETED"

    events_response = client.get(f"/api/v1/orchestrations/{technical_request['trace_id']}/events")
    event_types = [event["event_type"] for event in events_response.json()]
    assert "HUMAN_REVIEW_APPROVED" in event_types


@pytest.mark.llm
def test_requester_rejects_pending_request(client: TestClient, monkeypatch) -> None:
    technical_request = _create_request_pending_review(client, monkeypatch)

    response = client.post(
        f"/api/v1/requests/{technical_request['id']}/review",
        json={"decision": "reject", "notes": "Evidência insuficiente para prosseguir."},
        headers=authenticated_csrf_headers(client),
    )
    assert response.status_code == 200
    assert response.json()["status"] == "REJECTED"

    events_response = client.get(f"/api/v1/orchestrations/{technical_request['trace_id']}/events")
    event_types = [event["event_type"] for event in events_response.json()]
    assert "HUMAN_REVIEW_REJECTED" in event_types


def test_review_rejects_request_not_awaiting_review(client: TestClient) -> None:
    register(client, TECHNICIAN)

    technical_request = create_qualified_request(client, requested_domains=["codigo_legado"])

    response = client.post(
        f"/api/v1/requests/{technical_request['id']}/review",
        json={"decision": "approve"},
        headers=authenticated_csrf_headers(client),
    )
    assert response.status_code == 409


@pytest.mark.llm
def test_other_user_cannot_review_someone_elses_request(client: TestClient, monkeypatch) -> None:
    """A revisão humana é de quem abriu a solicitação: para outra pessoa ela
    simplesmente não existe (404, mesmo padrão owner-scoped do resto da API)."""
    technical_request = _create_request_pending_review(client, monkeypatch)

    client.post("/api/v1/auth/logout", headers=authenticated_csrf_headers(client))
    register(client, OUTSIDER)

    response = client.post(
        f"/api/v1/requests/{technical_request['id']}/review",
        json={"decision": "approve"},
        headers=authenticated_csrf_headers(client),
    )
    assert response.status_code == 404


def test_reject_requires_notes() -> None:
    from pydantic import ValidationError

    from app.schemas.orchestration import TechnicalRequestReview

    with pytest.raises(ValidationError):
        TechnicalRequestReview(decision="reject", notes="   ")
    assert TechnicalRequestReview(decision="approve").notes is None
    assert TechnicalRequestReview(decision="reject", notes="Sem evidência").notes == "Sem evidência"
