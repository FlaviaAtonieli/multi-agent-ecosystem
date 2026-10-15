import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

EXPORTED = Path(__file__).resolve().parent.parent.parent / "docs" / "api" / "openapi.json"


def _operations() -> list[tuple[str, str, dict]]:
    schema = app.openapi()
    return [(method, path, op) for path, ops in schema["paths"].items() for method, op in ops.items()]


def test_every_operation_is_documented() -> None:
    """Rota nova sem entrada em OPERATION_DOCS (app/api/openapi_docs.py) quebra aqui."""
    missing = [
        f"{method.upper()} {path}"
        for method, path, op in _operations()
        if not op.get("description") or not op.get("summary")
    ]
    assert missing == []


def test_every_tag_has_a_description() -> None:
    schema = app.openapi()
    described = {tag["name"] for tag in schema["tags"]}
    used = {tag for _, _, op in _operations() for tag in op.get("tags", [])}
    assert used <= described


def test_security_matches_route_dependencies() -> None:
    paths = app.openapi()["paths"]
    assert paths["/api/v1/health"]["get"]["security"] == []
    assert paths["/api/v1/auth/login"]["post"]["security"] == [{"csrfHeader": []}]
    assert paths["/api/v1/auth/me"]["get"]["security"] == [{"sessionCookie": []}]
    assert paths["/api/v1/clans"]["post"]["security"] == [{"sessionCookie": [], "csrfHeader": []}]


def test_exported_openapi_is_up_to_date() -> None:
    """Se falhar: rode `python scripts/export_openapi.py` a partir de backend/."""
    assert json.loads(EXPORTED.read_text(encoding="utf-8")) == json.loads(json.dumps(app.openapi()))


def test_swagger_ui_fills_csrf_header(client: TestClient) -> None:
    response = client.get("/docs")
    assert response.status_code == 200
    assert "requestInterceptor" in response.text
    assert "X-CSRF-Token" in response.text
