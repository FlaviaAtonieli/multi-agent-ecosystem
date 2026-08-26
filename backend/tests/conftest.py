import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

TEST_DB = Path(__file__).parent / "test_agenthub.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB.as_posix()}"
os.environ["AUTO_CREATE_TABLES"] = "true"
os.environ["COOKIE_SECURE"] = "false"
os.environ["ALLOW_REGISTRATION"] = "true"
os.environ["BOOTSTRAP_ADMIN_EMAIL"] = ""
os.environ["BOOTSTRAP_ADMIN_PASSWORD"] = ""
os.environ["CORS_ORIGINS"] = "http://localhost:5173"
os.environ["TRUSTED_HOSTS"] = "testserver,localhost,127.0.0.1"
# Real MCP client/server round-trips over stdio (subprocess spawn) are covered by
# one dedicated test; the rest of the suite uses the in-memory transport to stay fast.
os.environ["MCP_SKILL_TRANSPORT"] = "memory"

from app.core.database import Base, SessionLocal, engine  # noqa: E402
from app.core.rate_limit import limiter  # noqa: E402
from app.main import app  # noqa: E402
from app.models import User  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    limiter.clear()
    engine.dispose()
    if TEST_DB.exists():
        TEST_DB.unlink()
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as test_client:
        yield test_client
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    if TEST_DB.exists():
        TEST_DB.unlink()
    limiter.clear()


def csrf_headers(client: TestClient) -> dict[str, str]:
    response = client.get("/api/v1/auth/csrf")
    assert response.status_code == 200
    token = client.cookies.get("agenthub_csrf")
    assert token
    return {"X-CSRF-Token": token}


def authenticated_csrf_headers(client: TestClient) -> dict[str, str]:
    """Same CSRF cookie the current session already carries, without asking the
    server for a new one -- used after login/register, when re-fetching would
    just re-read the same cookie the client already has."""
    token = client.cookies.get("agenthub_csrf")
    assert token
    return {"X-CSRF-Token": token}


def register(client: TestClient, user: dict) -> None:
    response = client.post("/api/v1/auth/register", json=user, headers=csrf_headers(client))
    assert response.status_code == 201


def promote(email: str, role: str) -> str:
    """Writes the role directly to the DB, bypassing the admin HTTP endpoint.

    The active session isn't revoked (unlike the real ADMIN-driven role-change
    endpoint), so the same logged-in test client immediately acts under the
    new role on its next request -- no re-login needed mid-test.
    """
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        assert user is not None
        user.role = role
        db.commit()
        return user.id


def create_qualified_request(
    client: TestClient,
    *,
    title: str = "Avaliar limite de crédito por segmento",
    problem: str = "O limite de crédito é global e precisa considerar o segmento do cliente.",
    objective: str = "Gerar plano técnico sem executar alterações automaticamente.",
    context: str = (
        "O sistema legado calcula o limite de crédito do cliente de forma fixa, "
        "sem considerar o segmento, e isso precisa mudar com segurança."
    ),
    restrictions: list[str] | None = None,
    requested_domains: list[str] | None = None,
) -> dict:
    response = client.post(
        "/api/v1/requests",
        json={
            "title": title,
            "problem": problem,
            "objective": objective,
            "context": context,
            "restrictions": restrictions if restrictions is not None else ["Não executar tools"],
            "requested_domains": requested_domains or [],
        },
        headers=authenticated_csrf_headers(client),
    )
    assert response.status_code == 201
    assert response.json()["status"] == "QUALIFIED"
    return response.json()
