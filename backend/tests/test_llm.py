from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import settings
from app.core.database import SessionLocal
from app.models import LLMInvocation
from tests.conftest import (
    authenticated_csrf_headers,
    create_qualified_request,
    enable_real_llm,
    promote,
    register,
)

TECHNICIAN = {
    "name": "Tecnica Autorizada",
    "email": "tecnica.llm@example.com",
    "password": "StrongPassword!123",
}


def test_regular_user_cannot_access_llm_status(client: TestClient) -> None:
    register(client, TECHNICIAN)
    response = client.get("/api/v1/llm/status")
    assert response.status_code == 403


def test_openrouter_plan_is_traced_without_storing_content(
    client: TestClient,
    monkeypatch,
) -> None:
    register(client, TECHNICIAN)
    technician_id = promote(TECHNICIAN["email"], "TECHNICIAN")
    technical_request = create_qualified_request(
        client,
        title="Planejar análise técnica rastreável",
        problem=(
            "A integração apresenta divergência para tecnica.llm@example.com "
            "e contém password=SegredoTemporario! que deve ser mascarado."
        ),
        objective="Gerar um plano técnico sem executar alterações automaticamente.",
        context=(
            "A rotina é corporativa, possui dependências de API e banco de dados, "
            "e precisa de revisão humana antes de qualquer publicação."
        ),
        restrictions=["Não executar tools", "Não publicar automaticamente"],
    )

    enable_real_llm(monkeypatch)
    monkeypatch.setattr(settings, "llm_store_result_content", False)
    monkeypatch.setattr(settings, "llm_store_provider_response", False)

    status_response = client.get("/api/v1/llm/status")
    assert status_response.status_code == 200
    status_payload = status_response.json()
    assert status_payload["enabled"] is True
    assert status_payload["provider"] == "openrouter"
    assert "api_key" not in status_payload

    plan_response = client.post(
        f"/api/v1/llm/requests/{technical_request['id']}/plan",
        headers=authenticated_csrf_headers(client),
    )
    assert plan_response.status_code == 200
    plan_payload = plan_response.json()
    assert plan_payload["provider"] == "openrouter"
    assert plan_payload["trace_id"] == technical_request["trace_id"]
    # Prompted as a strict rule (RFC "humano no loop"), not just a mock default --
    # observed consistently against the real model, but real output can in
    # principle vary; if this ever flakes, it's evidence the prompt needs tightening.
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
