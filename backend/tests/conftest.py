import os
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

TEST_DB = Path(__file__).parent / "test_agenthub.db"
# Por padrão, SQLite. O CI também roda a suíte em PostgreSQL, o banco de produção.
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{TEST_DB.as_posix()}"
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
# O código de login por e-mail tem testes próprios (test_login_code.py), que o
# religam via monkeypatch; no resto da suíte o login cria a sessão direto.
os.environ["LOGIN_EMAIL_CODE_ENABLED"] = "false"
os.environ["EMAIL_BACKEND"] = "console"

# There is no mock LLM/embedding provider: tests that exercise planning or RAG
# call OpenRouter for real (see REAL_LLM_MODEL below). The key must already be a
# real env var (CI) or sit in the repo root .env (local dev, gitignored).
if not os.environ.get("OPENROUTER_API_KEY"):
    _root_env = Path(__file__).resolve().parent.parent.parent / ".env"
    if _root_env.exists():
        for _line in _root_env.read_text(encoding="utf-8").splitlines():
            if _line.startswith("OPENROUTER_API_KEY="):
                os.environ["OPENROUTER_API_KEY"] = _line.split("=", 1)[1].strip()
                break

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


# Pins a free model that declares structured_outputs: openrouter/free's random router
# landed on a model without it and returned incomplete JSON (2026-08-26). Not validated
# end-to-end yet; the previous pin left the free tier in 2026-11. Free tier: 50 req/day
# without purchased credits.
REAL_LLM_MODEL = "dots-studio/dots-3-note-preview:free"


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


def user_id_for(email: str) -> str:
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        assert user is not None
        return user.id


def create_test_clan(client: TestClient) -> str:
    """Clã novo com todas as skills ativas que o usuário logado enxerga agora."""
    headers = authenticated_csrf_headers(client)
    clan = client.post("/api/v1/clans", json={"name": f"Clã {uuid4().hex[:12]}"}, headers=headers)
    assert clan.status_code == 201, clan.text
    clan_id = clan.json()["id"]
    for skill in client.get("/api/v1/agent-skills?only_active=true").json():
        added = client.post(
            f"/api/v1/clans/{clan_id}/skills", json={"agent_skill_id": skill["id"]}, headers=headers
        )
        assert added.status_code == 201, added.text
    return clan_id


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
            "clan_id": create_test_clan(client),
        },
        headers=authenticated_csrf_headers(client),
    )
    assert response.status_code == 201
    assert response.json()["status"] == "QUALIFIED"
    return response.json()


def enable_real_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    """Points the app's LLM integration at a real OpenRouter call for this test.

    No mock exists: this is the one place every LLM-touching test configures
    the provider, so the model choice lives in one spot (REAL_LLM_MODEL above).
    """
    from app.core.config import settings

    monkeypatch.setattr(settings, "llm_enabled", True)
    monkeypatch.setattr(settings, "llm_provider", "openrouter")
    monkeypatch.setattr(settings, "llm_model", REAL_LLM_MODEL)
    monkeypatch.setattr(settings, "llm_allowed_models", REAL_LLM_MODEL)


def real_embedding_provider():
    """The only embedding provider available: OpenRouter's OpenAI-compatible
    embeddings endpoint. No mock exists, so RAG tests call it for real."""
    from app.core.config import settings
    from app.rag.providers.openrouter_embedding_provider import OpenRouterEmbeddingProvider

    return OpenRouterEmbeddingProvider(settings)
