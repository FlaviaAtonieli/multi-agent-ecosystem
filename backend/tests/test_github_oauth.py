from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.core.config import settings
from app.services.github_oauth_service import GitHubProfile
from tests.conftest import authenticated_csrf_headers, csrf_headers, register

PASSWORD_OWNER = {
    "name": "Dona Da Senha",
    "email": "dona.senha@example.com",
    "password": "StrongPassword!123",
}


def _enable_github_oauth(monkeypatch) -> None:
    monkeypatch.setattr(settings, "github_oauth_enabled", True)
    monkeypatch.setattr(settings, "github_client_id", "fake-client-id")
    monkeypatch.setattr(settings, "github_client_secret", SecretStr("fake-client-secret"))


def _stub_github_profile(
    monkeypatch,
    *,
    github_id: str = "990001",
    name: str = "Dev GitHub",
    email: str = "dev.github@example.com",
    avatar_url: str | None = "https://avatars.example/dev.png",
) -> None:
    monkeypatch.setattr(
        "app.api.v1.endpoints.auth.exchange_code_for_access_token",
        lambda code: "fake-access-token",  # noqa: ARG005
    )
    monkeypatch.setattr(
        "app.api.v1.endpoints.auth.fetch_github_profile",
        lambda token: GitHubProfile(  # noqa: ARG005
            github_id=github_id, name=name, email=email, avatar_url=avatar_url
        ),
    )


def _start_github_login(client: TestClient) -> str:
    """Hits /github/login to seed the state cookie (as a real browser would
    before landing on GitHub), and returns that state value for the caller
    to echo back on /github/callback."""
    response = client.get("/api/v1/auth/github/login", follow_redirects=False)
    assert response.status_code == 302
    state = client.cookies.get("agenthub_github_oauth_state")
    assert state
    return state


def test_github_login_disabled_returns_404(client: TestClient) -> None:
    response = client.get("/api/v1/auth/github/login", follow_redirects=False)
    assert response.status_code == 404


def test_github_login_redirects_to_authorize_url(client: TestClient, monkeypatch) -> None:
    _enable_github_oauth(monkeypatch)

    response = client.get("/api/v1/auth/github/login", follow_redirects=False)
    assert response.status_code == 302
    location = response.headers["location"]
    assert location.startswith("https://github.com/login/oauth/authorize?")
    assert "client_id=fake-client-id" in location
    assert "state=" in location
    assert client.cookies.get("agenthub_github_oauth_state")


def test_github_callback_creates_new_user_and_starts_session(client: TestClient, monkeypatch) -> None:
    _enable_github_oauth(monkeypatch)
    _stub_github_profile(monkeypatch, email="nova.conta@example.com")
    state = _start_github_login(client)

    response = client.get(
        "/api/v1/auth/github/callback",
        params={"code": "fake-code", "state": state},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["location"] == f"{settings.frontend_base_url}/dashboard"
    assert client.cookies.get(settings.session_cookie_name)
    assert not client.cookies.get("agenthub_github_oauth_state")

    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    payload = me.json()
    assert payload["email"] == "nova.conta@example.com"
    assert payload["name"] == "Dev GitHub"
    assert payload["role"] == "USER"
    assert payload["avatar_url"] == "https://avatars.example/dev.png"


def test_github_callback_reuses_existing_linked_account(client: TestClient, monkeypatch) -> None:
    _enable_github_oauth(monkeypatch)
    _stub_github_profile(monkeypatch, github_id="777001", email="mesma.conta@example.com")

    state = _start_github_login(client)
    first = client.get(
        "/api/v1/auth/github/callback",
        params={"code": "fake-code", "state": state},
        follow_redirects=False,
    )
    first_user_id = client.get("/api/v1/auth/me").json()["id"]
    client.post("/api/v1/auth/logout", headers=authenticated_csrf_headers(client))

    _stub_github_profile(
        monkeypatch, github_id="777001", name="Dev GitHub Renomeado", email="mesma.conta@example.com"
    )
    state = _start_github_login(client)
    second = client.get(
        "/api/v1/auth/github/callback",
        params={"code": "fake-code", "state": state},
        follow_redirects=False,
    )
    assert first.status_code == second.status_code == 302

    second_user = client.get("/api/v1/auth/me").json()
    assert second_user["id"] == first_user_id
    assert second_user["name"] == "Dev GitHub Renomeado"


def test_github_callback_state_mismatch_redirects_with_error(client: TestClient, monkeypatch) -> None:
    _enable_github_oauth(monkeypatch)
    _stub_github_profile(monkeypatch)
    _start_github_login(client)

    response = client.get(
        "/api/v1/auth/github/callback",
        params={"code": "fake-code", "state": "um-state-que-nao-bate"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["location"] == f"{settings.frontend_base_url}/login?error=github_oauth_failed"
    assert not client.cookies.get(settings.session_cookie_name)


def test_github_callback_email_already_used_by_password_account(client: TestClient, monkeypatch) -> None:
    register(client, PASSWORD_OWNER)
    client.post("/api/v1/auth/logout", headers=authenticated_csrf_headers(client))

    _enable_github_oauth(monkeypatch)
    _stub_github_profile(monkeypatch, github_id="123123", email=PASSWORD_OWNER["email"])
    state = _start_github_login(client)

    response = client.get(
        "/api/v1/auth/github/callback",
        params={"code": "fake-code", "state": state},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["location"] == f"{settings.frontend_base_url}/login?error=github_email_in_use"
    assert not client.cookies.get(settings.session_cookie_name)


def test_password_login_rejected_for_github_only_account(client: TestClient, monkeypatch) -> None:
    _enable_github_oauth(monkeypatch)
    _stub_github_profile(monkeypatch, email="so.github@example.com")
    state = _start_github_login(client)
    client.get(
        "/api/v1/auth/github/callback",
        params={"code": "fake-code", "state": state},
        follow_redirects=False,
    )
    client.post("/api/v1/auth/logout", headers=authenticated_csrf_headers(client))

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "so.github@example.com", "password": "QualquerSenha!123"},
        headers=csrf_headers(client),
    )
    assert response.status_code == 401
    assert "GitHub" in response.json()["message"]
