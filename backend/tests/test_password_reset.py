import re

import pytest
from fastapi.testclient import TestClient

from app.services.email_service import console_outbox
from tests.conftest import authenticated_csrf_headers, csrf_headers, register

USER = {
    "name": "Usuaria Esquecida",
    "email": "usuaria.esquecida@example.com",
    "password": "StrongPassword!123",
}
NEW_PASSWORD = "BrandNewPassword!456"


@pytest.fixture(autouse=True)
def _clear_outbox() -> None:
    console_outbox.clear()
    yield
    console_outbox.clear()


def _forgot(client: TestClient, email: str):
    return client.post("/api/v1/auth/password/forgot", json={"email": email}, headers=csrf_headers(client))


def _token_from_last_email() -> str:
    assert console_outbox, "nenhum e-mail foi enviado"
    match = re.search(r"reset-password\?token=([A-Za-z0-9_-]+)", console_outbox[-1].get_content())
    assert match
    return match.group(1)


def _reset(client: TestClient, token: str, password: str = NEW_PASSWORD):
    return client.post(
        "/api/v1/auth/password/reset",
        json={"token": token, "new_password": password},
        headers=csrf_headers(client),
    )


def _login(client: TestClient, password: str):
    return client.post(
        "/api/v1/auth/login",
        json={"email": USER["email"], "password": password},
        headers=csrf_headers(client),
    )


def test_reset_flow_changes_password(client: TestClient) -> None:
    register(client, USER)
    client.post("/api/v1/auth/logout", headers=authenticated_csrf_headers(client))

    response = _forgot(client, USER["email"])
    assert response.status_code == 202
    assert console_outbox[-1]["To"] == USER["email"]

    assert _reset(client, _token_from_last_email()).status_code == 204
    assert _login(client, USER["password"]).status_code == 401
    assert _login(client, NEW_PASSWORD).status_code == 200


def test_unknown_email_gets_same_response_and_no_email(client: TestClient) -> None:
    register(client, USER)
    known = _forgot(client, USER["email"])
    console_outbox.clear()

    unknown = _forgot(client, "ninguem@example.com")
    assert unknown.status_code == known.status_code == 202
    assert unknown.json() == known.json()
    assert console_outbox == []


def test_token_is_single_use(client: TestClient) -> None:
    register(client, USER)
    _forgot(client, USER["email"])
    token = _token_from_last_email()

    assert _reset(client, token).status_code == 204
    assert _reset(client, token, "AnotherPassword!789").status_code == 400


def test_new_request_invalidates_previous_link(client: TestClient) -> None:
    register(client, USER)
    _forgot(client, USER["email"])
    first_token = _token_from_last_email()
    _forgot(client, USER["email"])
    second_token = _token_from_last_email()

    assert _reset(client, first_token).status_code == 400
    assert _reset(client, second_token).status_code == 204


def test_reset_revokes_existing_sessions(client: TestClient) -> None:
    register(client, USER)  # sessão ativa neste cliente
    _forgot(client, USER["email"])

    assert _reset(client, _token_from_last_email()).status_code == 204
    assert client.get("/api/v1/auth/me").status_code == 401


def test_reset_rejects_weak_password(client: TestClient) -> None:
    register(client, USER)
    _forgot(client, USER["email"])

    assert _reset(client, _token_from_last_email(), "fraca").status_code == 422


def test_invalid_token_is_rejected(client: TestClient) -> None:
    assert _reset(client, "x" * 40).status_code == 400
