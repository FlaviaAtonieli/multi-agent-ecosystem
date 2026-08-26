from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.database import SessionLocal
from app.models import User
from tests.conftest import csrf_headers

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


def authenticated_csrf_headers(client: TestClient) -> dict[str, str]:
    token = client.cookies.get("agenthub_csrf")
    assert token
    return {"X-CSRF-Token": token}


def register(client: TestClient, user: dict) -> None:
    response = client.post("/api/v1/auth/register", json=user, headers=csrf_headers(client))
    assert response.status_code == 201


def promote(email: str, role: str) -> str:
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        assert user is not None
        user.role = role
        db.commit()
        return user.id


def create_qualified_request(client: TestClient, *, requested_domains: list[str]) -> dict:
    response = client.post(
        "/api/v1/requests",
        json={
            "title": "Avaliar limite de crédito por segmento",
            "problem": "O limite de crédito é global e precisa considerar o segmento do cliente.",
            "objective": "Gerar plano técnico sem executar alterações automaticamente.",
            "context": (
                "O sistema legado calcula o limite de crédito do cliente de forma fixa, "
                "sem considerar o segmento, e isso precisa mudar com segurança."
            ),
            "restrictions": ["Não executar tools"],
            "requested_domains": requested_domains,
        },
        headers=authenticated_csrf_headers(client),
    )
    assert response.status_code == 201
    assert response.json()["status"] == "QUALIFIED"
    return response.json()


def _create_request_pending_review(client: TestClient, monkeypatch) -> dict:
    """Executes a skill with no knowledge base ingested: zero retrieved chunks
    forces BAIXO confidence in LegacyCodeSkillExecutor, so the Quality Gate
    rejects and flags requires_human_review — a deterministic way to land a
    request in VALIDATING without depending on LLM output variance."""
    from app.core.config import settings

    register(client, TECHNICIAN)
    promote(TECHNICIAN["email"], "TECHNICIAN")

    client.post(
        "/api/v1/agent-skills/import",
        json={"manifest_markdown": FIXTURE_MANIFEST},
        headers=authenticated_csrf_headers(client),
    )

    technical_request = create_qualified_request(client, requested_domains=["codigo_legado"])

    monkeypatch.setattr(settings, "llm_enabled", True)
    monkeypatch.setattr(settings, "llm_provider", "mock")

    execution_response = client.post(
        f"/api/v1/agent-skills/requests/{technical_request['id']}/execute",
        headers=authenticated_csrf_headers(client),
    )
    assert execution_response.status_code == 200
    assert execution_response.json()["verdict"]["requires_human_review"] is True

    detail_response = client.get(f"/api/v1/requests/{technical_request['id']}")
    assert detail_response.json()["status"] == "VALIDATING"
    return technical_request


def test_reviewer_approves_pending_request(client: TestClient, monkeypatch) -> None:
    technical_request = _create_request_pending_review(client, monkeypatch)

    promote(TECHNICIAN["email"], "REVIEWER")
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


def test_reviewer_rejects_pending_request(client: TestClient, monkeypatch) -> None:
    technical_request = _create_request_pending_review(client, monkeypatch)

    promote(TECHNICIAN["email"], "REVIEWER")
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


def test_review_requires_reviewer_or_admin_role(client: TestClient, monkeypatch) -> None:
    technical_request = _create_request_pending_review(client, monkeypatch)

    # Still TECHNICIAN, never promoted to REVIEWER/ADMIN.
    response = client.post(
        f"/api/v1/requests/{technical_request['id']}/review",
        json={"decision": "approve"},
        headers=authenticated_csrf_headers(client),
    )
    assert response.status_code == 403


def test_review_rejects_request_not_awaiting_review(client: TestClient) -> None:
    register(client, TECHNICIAN)
    promote(TECHNICIAN["email"], "REVIEWER")

    technical_request = create_qualified_request(client, requested_domains=["codigo_legado"])

    response = client.post(
        f"/api/v1/requests/{technical_request['id']}/review",
        json={"decision": "approve"},
        headers=authenticated_csrf_headers(client),
    )
    assert response.status_code == 409


def test_reviewer_can_review_another_users_request(client: TestClient, monkeypatch) -> None:
    technical_request = _create_request_pending_review(client, monkeypatch)

    client.post("/api/v1/auth/logout", headers=authenticated_csrf_headers(client))
    register(client, OUTSIDER)
    promote(OUTSIDER["email"], "REVIEWER")

    response = client.post(
        f"/api/v1/requests/{technical_request['id']}/review",
        json={"decision": "approve"},
        headers=authenticated_csrf_headers(client),
    )
    assert response.status_code == 200
    assert response.json()["status"] == "COMPLETED"
