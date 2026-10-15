import re

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.core.config import settings
from app.services.email_service import console_outbox
from app.services.github_oauth_service import GitHubProfile
from tests.conftest import authenticated_csrf_headers, csrf_headers, register

USER = {"name": "Usuaria Codigo", "email": "usuaria.codigo@example.com", "password": "StrongPassword!123"}


@pytest.fixture(autouse=True)
def _enable_login_code(monkeypatch) -> None:
    monkeypatch.setattr(settings, "login_email_code_enabled", True)
    monkeypatch.setattr(settings, "email_backend", "console")
    console_outbox.clear()
    yield
    console_outbox.clear()


def _last_code() -> str:
    assert console_outbox, "nenhum e-mail foi enviado"
    match = re.search(r"\b(\d{6})\b", console_outbox[-1]["Subject"])
    assert match
    return match.group(1)


def _password_login(client: TestClient):
    return client.post(
        "/api/v1/auth/login",
        json={"email": USER["email"], "password": USER["password"]},
        headers=csrf_headers(client),
    )


def _register_and_logout(client: TestClient) -> None:
    register(client, USER)
    client.post("/api/v1/auth/logout", headers=authenticated_csrf_headers(client))


def _verify(client: TestClient, code: str):
    return client.post("/api/v1/auth/login/verify", json={"code": code}, headers=csrf_headers(client))


def test_login_on_new_device_requires_code(client: TestClient) -> None:
    _register_and_logout(client)

    response = _password_login(client)
    assert response.status_code == 202
    assert response.json()["verification_required"] is True
    assert response.json()["email_hint"].endswith("@example.com")
    assert USER["email"] not in response.json()["email_hint"]  # e-mail mascarado
    assert console_outbox[-1]["To"] == USER["email"]

    # Sem confirmar o código, não há sessão.
    assert client.get("/api/v1/auth/me").status_code == 401

    verified = _verify(client, _last_code())
    assert verified.status_code == 200
    assert verified.json()["user"]["email"] == USER["email"]
    assert client.get("/api/v1/auth/me").status_code == 200


def test_trusted_device_skips_code_on_next_login(client: TestClient) -> None:
    _register_and_logout(client)
    _password_login(client)
    _verify(client, _last_code())
    client.post("/api/v1/auth/logout", headers=authenticated_csrf_headers(client))
    console_outbox.clear()

    response = _password_login(client)
    assert response.status_code == 200
    assert "user" in response.json()
    assert console_outbox == []


def test_other_browser_still_requires_code(client: TestClient) -> None:
    _register_and_logout(client)
    _password_login(client)
    _verify(client, _last_code())
    client.post("/api/v1/auth/logout", headers=authenticated_csrf_headers(client))

    # Simula outro navegador: sem o cookie de dispositivo confiável.
    client.cookies.clear()
    assert _password_login(client).status_code == 202


def test_wrong_code_counts_attempts_and_locks_challenge(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(settings, "login_code_max_attempts", 3)
    _register_and_logout(client)
    _password_login(client)
    right_code = _last_code()
    wrong_code = "000000" if right_code != "000000" else "111111"

    first = _verify(client, wrong_code)
    assert first.status_code == 400
    assert "2 tentativas" in first.json()["message"]
    assert _verify(client, wrong_code).status_code == 400

    locked = _verify(client, wrong_code)
    assert locked.status_code == 410
    # Nem o código certo vale mais depois de esgotar as tentativas.
    assert _verify(client, right_code).status_code == 410


def test_code_is_bound_to_the_browser_that_logged_in(client: TestClient) -> None:
    _register_and_logout(client)
    _password_login(client)
    code = _last_code()

    client.cookies.clear()
    response = _verify(client, code)
    assert response.status_code == 410


def test_resend_respects_cooldown_and_sends_new_code(client: TestClient, monkeypatch) -> None:
    _register_and_logout(client)
    _password_login(client)
    first_code = _last_code()

    too_soon = client.post("/api/v1/auth/login/resend", headers=csrf_headers(client))
    assert too_soon.status_code == 429

    monkeypatch.setattr(settings, "login_code_resend_cooldown_seconds", 0)
    resent = client.post("/api/v1/auth/login/resend", headers=csrf_headers(client))
    assert resent.status_code == 200
    assert len(console_outbox) == 2

    new_code = _last_code()
    if new_code != first_code:
        assert _verify(client, first_code).status_code == 400  # o código antigo deixa de valer
    assert _verify(client, new_code).status_code == 200


def test_password_change_revokes_trusted_devices(client: TestClient) -> None:
    _register_and_logout(client)
    _password_login(client)
    _verify(client, _last_code())

    new_password = "OtherStrongPassword!456"
    changed = client.post(
        "/api/v1/auth/me/password",
        json={"current_password": USER["password"], "new_password": new_password},
        headers=authenticated_csrf_headers(client),
    )
    assert changed.status_code == 200
    client.post("/api/v1/auth/logout", headers=authenticated_csrf_headers(client))

    response = client.post(
        "/api/v1/auth/login",
        json={"email": USER["email"], "password": new_password},
        headers=csrf_headers(client),
    )
    assert response.status_code == 202


def test_challenge_status_endpoint(client: TestClient) -> None:
    assert client.get("/api/v1/auth/login/challenge").status_code == 410

    _register_and_logout(client)
    _password_login(client)
    response = client.get("/api/v1/auth/login/challenge")
    assert response.status_code == 200
    assert response.json()["email_hint"].endswith("@example.com")


def test_github_login_on_new_device_requires_code(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(settings, "github_oauth_enabled", True)
    monkeypatch.setattr(settings, "github_client_id", "fake-client-id")
    monkeypatch.setattr(settings, "github_client_secret", SecretStr("fake-client-secret"))
    monkeypatch.setattr("app.api.v1.endpoints.auth.exchange_code_for_access_token", lambda code: "token")
    monkeypatch.setattr(
        "app.api.v1.endpoints.auth.fetch_github_profile",
        lambda token: GitHubProfile(
            github_id="770001", name="Dev Codigo", email="dev.codigo@example.com", avatar_url=None
        ),
    )

    client.get("/api/v1/auth/github/login", follow_redirects=False)
    state = client.cookies.get("agenthub_github_oauth_state")
    response = client.get(
        "/api/v1/auth/github/callback", params={"code": "c", "state": state}, follow_redirects=False
    )

    assert response.status_code == 302
    assert response.headers["location"] == f"{settings.frontend_base_url}/login?verify=1"
    assert client.get("/api/v1/auth/me").status_code == 401
    assert console_outbox[-1]["To"] == "dev.codigo@example.com"

    assert _verify(client, _last_code()).status_code == 200
    assert client.get("/api/v1/auth/me").json()["email"] == "dev.codigo@example.com"
