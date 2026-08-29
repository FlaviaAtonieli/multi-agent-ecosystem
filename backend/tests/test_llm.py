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


def _seed_completed_invocation(
    user_id: str, technical_request_id: str, trace_id: str, *, input_tokens: int, output_tokens: int
) -> None:
    """Writes a COMPLETED LLMInvocation directly, bypassing a real call -- used to
    put a user's daily token usage above a quota without spending API credits,
    since the quota check runs before any provider call is made."""
    from uuid import uuid4

    with SessionLocal() as db:
        db.add(
            LLMInvocation(
                technical_request_id=technical_request_id,
                user_id=user_id,
                trace_id=trace_id,
                llm_call_id=str(uuid4()),
                provider="openrouter",
                model="seed-model",
                purpose="TECHNICAL_PLANNING",
                prompt_template_id="technical-planner",
                prompt_template_version="v1",
                input_hash="0" * 64,
                status="COMPLETED",
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )
        )
        db.commit()


def test_daily_token_quota_blocks_further_calls(client: TestClient, monkeypatch) -> None:
    register(client, TECHNICIAN)
    technician_id = promote(TECHNICIAN["email"], "TECHNICIAN")
    technical_request = create_qualified_request(client)

    enable_real_llm(monkeypatch)
    monkeypatch.setattr(settings, "llm_daily_token_limit_per_user", 100)
    _seed_completed_invocation(
        technician_id,
        technical_request["id"],
        technical_request["trace_id"],
        input_tokens=80,
        output_tokens=30,
    )

    plan_response = client.post(
        f"/api/v1/llm/requests/{technical_request['id']}/plan",
        headers=authenticated_csrf_headers(client),
    )
    assert plan_response.status_code == 429
    assert "Limite diário" in plan_response.json()["message"]

    status_response = client.get("/api/v1/llm/status")
    assert status_response.json()["tokens_used_today"] == 110
    assert status_response.json()["daily_token_limit_per_user"] == 100


def test_admin_is_exempt_from_daily_token_quota(client: TestClient, monkeypatch) -> None:
    admin = {
        "name": "Admin Cotas",
        "email": "admin.cotas@example.com",
        "password": "StrongPassword!123",
    }
    register(client, admin)
    admin_id = promote(admin["email"], "ADMIN")
    technical_request = create_qualified_request(client)

    enable_real_llm(monkeypatch)
    monkeypatch.setattr(settings, "llm_daily_token_limit_per_user", 100)
    _seed_completed_invocation(
        admin_id,
        technical_request["id"],
        technical_request["trace_id"],
        input_tokens=10_000,
        output_tokens=10_000,
    )

    plan_response = client.post(
        f"/api/v1/llm/requests/{technical_request['id']}/plan",
        headers=authenticated_csrf_headers(client),
    )
    assert plan_response.status_code == 200
