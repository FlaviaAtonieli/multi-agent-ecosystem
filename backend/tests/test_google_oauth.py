from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.core.config import settings
from app.services.google_oauth_service import GoogleProfile
from tests.conftest import authenticated_csrf_headers, csrf_headers, register

PASSWORD_OWNER = {
    "name": "Dona Da Senha",
    "email": "dona.senha.google@example.com",
    "password": "StrongPassword!123",
}


def _enable_google_oauth(monkeypatch) -> None:
    monkeypatch.setattr(settings, "google_oauth_enabled", True)
    monkeypatch.setattr(settings, "google_client_id", "fake-client-id")
    monkeypatch.setattr(settings, "google_client_secret", SecretStr("fake-client-secret"))


def _stub_google_profile(
    monkeypatch,
    *,
    google_id: str = "110001",
    name: str = "Dev Google",
    email: str = "dev.google@example.com",
    avatar_url: str | None = "https://avatars.example/dev-google.png",
) -> None:
    monkeypatch.setattr(
        "app.api.v1.endpoints.auth.exchange_google_code_for_access_token",
        lambda code: "fake-access-token",  # noqa: ARG005
    )
    monkeypatch.setattr(
        "app.api.v1.endpoints.auth.fetch_google_profile",
        lambda token: GoogleProfile(  # noqa: ARG005
            google_id=google_id, name=name, email=email, avatar_url=avatar_url
        ),
    )


def _start_google_login(client: TestClient) -> str:
    """Hits /google/login to seed the state cookie (as a real browser would
    before landing on Google), and returns that state value for the caller
    to echo back on /google/callback."""
    response = client.get("/api/v1/auth/google/login", follow_redirects=False)
    assert response.status_code == 302
    state = client.cookies.get("agenthub_google_oauth_state")
    assert state
    return state


def test_google_login_disabled_returns_404(client: TestClient) -> None:
    response = client.get("/api/v1/auth/google/login", follow_redirects=False)
    assert response.status_code == 404


def test_google_login_redirects_to_authorize_url(client: TestClient, monkeypatch) -> None:
    _enable_google_oauth(monkeypatch)

    response = client.get("/api/v1/auth/google/login", follow_redirects=False)
    assert response.status_code == 302
    location = response.headers["location"]
    assert location.startswith("https://accounts.google.com/o/oauth2/v2/auth?")
    assert "client_id=fake-client-id" in location
    assert "state=" in location
    assert client.cookies.get("agenthub_google_oauth_state")


def test_google_callback_creates_new_user_and_starts_session(client: TestClient, monkeypatch) -> None:
    _enable_google_oauth(monkeypatch)
    _stub_google_profile(monkeypatch, email="nova.conta.google@example.com")
    state = _start_google_login(client)

    response = client.get(
        "/api/v1/auth/google/callback",
        params={"code": "fake-code", "state": state},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["location"] == f"{settings.frontend_base_url}/dashboard"
    assert client.cookies.get(settings.session_cookie_name)
    assert not client.cookies.get("agenthub_google_oauth_state")

    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    payload = me.json()
    assert payload["email"] == "nova.conta.google@example.com"
    assert payload["name"] == "Dev Google"
    assert payload["role"] == "USER"
    assert payload["avatar_url"] == "https://avatars.example/dev-google.png"
    assert payload["oauth_provider"] == "google"


def test_google_callback_reuses_existing_linked_account(client: TestClient, monkeypatch) -> None:
    _enable_google_oauth(monkeypatch)
    _stub_google_profile(monkeypatch, google_id="770001", email="mesma.conta.google@example.com")

    state = _start_google_login(client)
    first = client.get(
        "/api/v1/auth/google/callback",
        params={"code": "fake-code", "state": state},
        follow_redirects=False,
    )
    first_user_id = client.get("/api/v1/auth/me").json()["id"]
    client.post("/api/v1/auth/logout", headers=authenticated_csrf_headers(client))

    _stub_google_profile(
        monkeypatch, google_id="770001", name="Dev Google Renomeado", email="mesma.conta.google@example.com"
    )
    state = _start_google_login(client)
    second = client.get(
        "/api/v1/auth/google/callback",
        params={"code": "fake-code", "state": state},
        follow_redirects=False,
    )
    assert first.status_code == second.status_code == 302

    second_user = client.get("/api/v1/auth/me").json()
    assert second_user["id"] == first_user_id
    assert second_user["name"] == "Dev Google Renomeado"


def test_google_callback_state_mismatch_redirects_with_error(client: TestClient, monkeypatch) -> None:
    _enable_google_oauth(monkeypatch)
    _stub_google_profile(monkeypatch)
    _start_google_login(client)

    response = client.get(
        "/api/v1/auth/google/callback",
        params={"code": "fake-code", "state": "um-state-que-nao-bate"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["location"] == f"{settings.frontend_base_url}/login?error=google_oauth_failed"
    assert not client.cookies.get(settings.session_cookie_name)


def test_google_callback_email_already_used_by_password_account(client: TestClient, monkeypatch) -> None:
    register(client, PASSWORD_OWNER)
    client.post("/api/v1/auth/logout", headers=authenticated_csrf_headers(client))

    _enable_google_oauth(monkeypatch)
    _stub_google_profile(monkeypatch, google_id="123123", email=PASSWORD_OWNER["email"])
    state = _start_google_login(client)

    response = client.get(
        "/api/v1/auth/google/callback",
        params={"code": "fake-code", "state": state},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["location"] == f"{settings.frontend_base_url}/login?error=google_email_in_use"
    assert not client.cookies.get(settings.session_cookie_name)


def test_password_login_rejected_for_google_only_account(client: TestClient, monkeypatch) -> None:
    _enable_google_oauth(monkeypatch)
    _stub_google_profile(monkeypatch, email="so.google@example.com")
    state = _start_google_login(client)
    client.get(
        "/api/v1/auth/google/callback",
        params={"code": "fake-code", "state": state},
        follow_redirects=False,
    )
    client.post("/api/v1/auth/logout", headers=authenticated_csrf_headers(client))

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "so.google@example.com", "password": "QualquerSenha!123"},
        headers=csrf_headers(client),
    )
    assert response.status_code == 401
    assert "Google" in response.json()["message"]
