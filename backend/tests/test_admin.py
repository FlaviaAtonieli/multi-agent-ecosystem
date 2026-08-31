from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.models import LLMInvocation
from tests.conftest import (
    authenticated_csrf_headers,
    create_qualified_request,
    promote,
    register,
)

ADMIN = {
    "name": "Admin Painel",
    "email": "admin.painel@example.com",
    "password": "StrongPassword!123",
}
OUTSIDER = {
    "name": "Sem Acesso",
    "email": "sem.acesso@example.com",
    "password": "StrongPassword!123",
}


def _seed_completed_invocation(
    user_id: str, technical_request_id: str, trace_id: str, *, tokens: int
) -> None:
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
                input_tokens=tokens // 2,
                output_tokens=tokens - tokens // 2,
            )
        )
        db.commit()


def test_list_users_requires_admin(client: TestClient) -> None:
    register(client, OUTSIDER)
    response = client.get("/api/v1/admin/users")
    assert response.status_code == 403


def test_admin_lists_users_with_token_usage(client: TestClient) -> None:
    register(client, OUTSIDER)
    technical_request = create_qualified_request(client)
    outsider_id = promote(OUTSIDER["email"], "TECHNICIAN")
    _seed_completed_invocation(
        outsider_id, technical_request["id"], technical_request["trace_id"], tokens=1234
    )

    client.post("/api/v1/auth/logout", headers=authenticated_csrf_headers(client))
    register(client, ADMIN)
    promote(ADMIN["email"], "ADMIN")

    response = client.get("/api/v1/admin/users", headers=authenticated_csrf_headers(client))
    assert response.status_code == 200
    payload = response.json()

    outsider_row = next(item for item in payload if item["id"] == outsider_id)
    assert outsider_row["tokens_used_today"] == 1234
    assert outsider_row["daily_token_limit_per_user"] > 0
    assert outsider_row["role"] == "TECHNICIAN"

    admin_row = next(item for item in payload if item["email"] == ADMIN["email"])
    assert admin_row["tokens_used_today"] == 0


def test_admin_can_change_role_and_response_reflects_it(client: TestClient) -> None:
    register(client, OUTSIDER)
    outsider_id = promote(OUTSIDER["email"], "USER")

    client.post("/api/v1/auth/logout", headers=authenticated_csrf_headers(client))
    register(client, ADMIN)
    promote(ADMIN["email"], "ADMIN")

    response = client.patch(
        f"/api/v1/admin/users/{outsider_id}/role",
        json={"role": "TECHNICIAN"},
        headers=authenticated_csrf_headers(client),
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["role"] == "TECHNICIAN"
    assert payload["tokens_used_today"] == 0
    assert payload["daily_token_limit_per_user"] > 0


def test_admin_cannot_remove_own_admin_role(client: TestClient) -> None:
    register(client, ADMIN)
    admin_id = promote(ADMIN["email"], "ADMIN")

    response = client.patch(
        f"/api/v1/admin/users/{admin_id}/role",
        json={"role": "USER"},
        headers=authenticated_csrf_headers(client),
    )
    assert response.status_code == 400


def test_admin_can_deactivate_another_user(client: TestClient) -> None:
    register(client, OUTSIDER)
    outsider_id = promote(OUTSIDER["email"], "USER")

    client.post("/api/v1/auth/logout", headers=authenticated_csrf_headers(client))
    register(client, ADMIN)
    promote(ADMIN["email"], "ADMIN")

    response = client.patch(
        f"/api/v1/admin/users/{outsider_id}/status",
        json={"is_active": False},
        headers=authenticated_csrf_headers(client),
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is False
