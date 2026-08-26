from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import settings
from app.core.database import SessionLocal
from app.models import LLMInvocation, User
from tests.conftest import csrf_headers

TECHNICIAN = {
    "name": "Tecnica Autorizada",
    "email": "tecnica.llm@example.com",
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
            "title": "Planejar análise técnica rastreável",
            "problem": (
                "A integração apresenta divergência para tecnica.llm@example.com "
                "e contém password=SegredoTemporario! que deve ser mascarado."
            ),
            "objective": "Gerar um plano técnico sem executar alterações automaticamente.",
            "context": (
                "A rotina é corporativa, possui dependências de API e banco de dados, "
                "e precisa de revisão humana antes de qualquer publicação."
            ),
            "restrictions": ["Não executar tools", "Não publicar automaticamente"],
        },
        headers=authenticated_csrf_headers(client),
    )
    assert response.status_code == 201
    assert response.json()["status"] == "QUALIFIED"
    return response.json()


def test_regular_user_cannot_access_llm_status(client: TestClient) -> None:
    register_user(client)
    response = client.get("/api/v1/llm/status")
    assert response.status_code == 403


def test_mock_provider_plan_is_traced_without_storing_content(
    client: TestClient,
    monkeypatch,
) -> None:
    register_user(client)
    technician_id = promote_current_user_to_technician()
    technical_request = create_qualified_request(client)

    monkeypatch.setattr(settings, "llm_enabled", True)
    monkeypatch.setattr(settings, "llm_provider", "mock")
    monkeypatch.setattr(settings, "llm_model", "gpt-5-mini")
    monkeypatch.setattr(settings, "llm_store_result_content", False)
    monkeypatch.setattr(settings, "llm_store_provider_response", False)

    status_response = client.get("/api/v1/llm/status")
    assert status_response.status_code == 200
    status_payload = status_response.json()
    assert status_payload["enabled"] is True
    assert status_payload["provider"] == "mock"
    assert "api_key" not in status_payload

    plan_response = client.post(
        f"/api/v1/llm/requests/{technical_request['id']}/plan",
        headers=authenticated_csrf_headers(client),
    )
    assert plan_response.status_code == 200
    plan_payload = plan_response.json()
    assert plan_payload["provider"] == "mock"
    assert plan_payload["trace_id"] == technical_request["trace_id"]
    assert plan_payload["plan"]["requires_human_approval"] is True
    assert plan_payload["llm_call_id"]

    trace_response = client.get(
        f"/api/v1/llm/invocations/{technical_request['trace_id']}"
    )
    assert trace_response.status_code == 200
    invocations = trace_response.json()
    assert len(invocations) == 1
    assert invocations[0]["status"] == "COMPLETED"
    assert invocations[0]["redacted_fields_count"] >= 2
    assert len(invocations[0]["input_hash"]) == 64
    assert len(invocations[0]["output_hash"]) == 64

    with SessionLocal() as db:
        invocation = db.scalar(
            select(LLMInvocation).where(
                LLMInvocation.llm_call_id == plan_payload["llm_call_id"]
            )
        )
        assert invocation is not None
        assert invocation.user_id == technician_id
        assert invocation.result_payload is None
