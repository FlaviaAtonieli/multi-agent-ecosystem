import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

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

from app.core.database import Base, engine  # noqa: E402
from app.core.rate_limit import limiter  # noqa: E402
from app.main import app  # noqa: E402


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
