from fastapi.testclient import TestClient

from tests.conftest import authenticated_csrf_headers, csrf_headers, register

VALID_USER = {
    "name": "Flavia Souza",
    "email": "flavia@example.com",
    "password": "StrongPassword!123",
}


def test_health_check(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_registration_creates_secure_session_and_allows_dashboard(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json=VALID_USER,
        headers=csrf_headers(client),
    )

    assert response.status_code == 201
    assert response.json()["user"]["email"] == VALID_USER["email"]
    assert client.cookies.get("agenthub_session")
    assert client.cookies.get("agenthub_csrf")
    assert "HttpOnly" in response.headers.get("set-cookie", "")

    me_response = client.get("/api/v1/auth/me")
    assert me_response.status_code == 200
    assert me_response.json()["name"] == VALID_USER["name"]

    dashboard_response = client.get("/api/v1/dashboard/summary")
    assert dashboard_response.status_code == 200
    assert dashboard_response.json()["active_sessions"] == 1
    assert dashboard_response.json()["registered_agent_skills"] == 0


def test_login_uses_generic_error_for_unknown_credentials(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "unknown@example.com", "password": "WrongPassword!123"},
        headers=csrf_headers(client),
    )

    assert response.status_code == 401
    assert response.json()["message"] == "Email ou senha inválidos."


def test_csrf_is_required_for_state_changing_requests(client: TestClient) -> None:
    response = client.post("/api/v1/auth/register", json=VALID_USER)
    assert response.status_code == 403


def test_logout_revokes_session(client: TestClient) -> None:
    client.post(
        "/api/v1/auth/register",
        json=VALID_USER,
        headers=csrf_headers(client),
    )

    csrf_token = client.cookies.get("agenthub_csrf")
    response = client.post(
        "/api/v1/auth/logout",
        headers={"X-CSRF-Token": csrf_token},
    )
    assert response.status_code == 204

    me_response = client.get("/api/v1/auth/me")
    assert me_response.status_code == 401


def test_onboarding_starts_unset_and_can_be_completed(client: TestClient) -> None:
    register(client, VALID_USER)

    me_response = client.get("/api/v1/auth/me")
    assert me_response.json()["onboarding_completed_at"] is None

    complete_response = client.post(
        "/api/v1/auth/onboarding/complete", headers=authenticated_csrf_headers(client)
    )
    assert complete_response.status_code == 200
    assert complete_response.json()["onboarding_completed_at"] is not None

    me_after = client.get("/api/v1/auth/me")
    assert me_after.json()["onboarding_completed_at"] is not None


def test_onboarding_complete_is_idempotent(client: TestClient) -> None:
    register(client, VALID_USER)

    first = client.post("/api/v1/auth/onboarding/complete", headers=authenticated_csrf_headers(client))
    second = client.post("/api/v1/auth/onboarding/complete", headers=authenticated_csrf_headers(client))
    assert first.json()["onboarding_completed_at"] == second.json()["onboarding_completed_at"]
