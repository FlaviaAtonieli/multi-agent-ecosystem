from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.database import SessionLocal
from app.models import AuthSession, Clan, User
from tests.conftest import authenticated_csrf_headers, csrf_headers, register

USER = {
    "name": "Nome Original",
    "email": "conta.teste@example.com",
    "password": "StrongPassword!123",
}


def test_update_name_changes_display_name(client: TestClient) -> None:
    register(client, USER)
    response = client.patch(
        "/api/v1/auth/me",
        json={"name": "Nome Novo"},
        headers=authenticated_csrf_headers(client),
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Nome Novo"

    me_response = client.get("/api/v1/auth/me")
    assert me_response.json()["name"] == "Nome Novo"


def test_me_reports_has_password_true_for_password_account(client: TestClient) -> None:
    register(client, USER)
    response = client.get("/api/v1/auth/me")
    assert response.json()["has_password"] is True


def test_change_password_success(client: TestClient) -> None:
    register(client, USER)
    response = client.post(
        "/api/v1/auth/me/password",
        json={"current_password": USER["password"], "new_password": "AnotherStrong!456"},
        headers=authenticated_csrf_headers(client),
    )
    assert response.status_code == 200

    client.post("/api/v1/auth/logout", headers=authenticated_csrf_headers(client))
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": USER["email"], "password": "AnotherStrong!456"},
        headers=csrf_headers(client),
    )
    assert login_response.status_code == 200


def test_change_password_wrong_current_password_is_rejected(client: TestClient) -> None:
    register(client, USER)
    response = client.post(
        "/api/v1/auth/me/password",
        json={"current_password": "NotTheRealPassword!1", "new_password": "AnotherStrong!456"},
        headers=authenticated_csrf_headers(client),
    )
    assert response.status_code == 401


def test_change_password_rejected_for_github_only_account(client: TestClient) -> None:
    register(client, USER)
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == USER["email"]))
        user.password_hash = None  # simulates a GitHub-linked account
        db.commit()

    response = client.post(
        "/api/v1/auth/me/password",
        json={"current_password": USER["password"], "new_password": "AnotherStrong!456"},
        headers=authenticated_csrf_headers(client),
    )
    assert response.status_code == 409


def test_delete_account_soft_deletes_and_revokes_session(client: TestClient) -> None:
    register(client, USER)
    user_id = client.get("/api/v1/auth/me").json()["id"]

    response = client.delete("/api/v1/auth/me", headers=authenticated_csrf_headers(client))
    assert response.status_code == 204

    # session was revoked and cookies cleared -- /me now fails.
    me_response = client.get("/api/v1/auth/me")
    assert me_response.status_code == 401

    with SessionLocal() as db:
        user = db.get(User, user_id)
        assert user is not None  # row preserved, not hard-deleted
        assert user.is_active is False
        assert user.name == "Conta removida"
        assert user.email != USER["email"]
        assert user.password_hash is None

        remaining_sessions = db.scalars(
            select(AuthSession).where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
        ).all()
        assert remaining_sessions == []


def test_delete_account_preserves_data_the_user_created(client: TestClient) -> None:
    register(client, USER)
    create_response = client.post(
        "/api/v1/clans",
        json={"name": "Cla Que Sobrevive"},
        headers=authenticated_csrf_headers(client),
    )
    clan_id = create_response.json()["id"]

    client.delete("/api/v1/auth/me", headers=authenticated_csrf_headers(client))

    with SessionLocal() as db:
        clan = db.get(Clan, clan_id)
        assert clan is not None
        assert clan.name == "Cla Que Sobrevive"
