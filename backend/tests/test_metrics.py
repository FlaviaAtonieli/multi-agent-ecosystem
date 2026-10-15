import re

from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.core.config import settings
from tests.conftest import register

USER = {
    "name": "Usuaria Metricas",
    "email": "usuaria.metricas@example.com",
    "password": "StrongPassword!123",
}


def _metric_value(text: str, name: str, **labels: str) -> float:
    for line in text.splitlines():
        if not line.startswith(name):
            continue
        if all(f'{key}="{value}"' in line for key, value in labels.items()):
            return float(line.rsplit(" ", 1)[1])
    return 0.0


def test_metrics_endpoint_exposes_http_metrics_by_route_template(client: TestClient) -> None:
    client.get("/api/v1/health")
    client.get("/api/v1/requests/nao-existe")  # 401, mas a rota existe
    client.get("/api/v1/rota-que-nao-existe")

    response = client.get("/metrics")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    text = response.text

    assert _metric_value(text, "agenthub_http_requests_total", route="/api/v1/health", status="200") >= 1
    # Template da rota, nunca o id concreto -- evita uma série por URL.
    assert _metric_value(text, "agenthub_http_requests_total", route="/api/v1/requests/{request_id}") >= 1
    assert "nao-existe" not in text
    assert _metric_value(text, "agenthub_http_requests_total", route="unmatched", status="404") >= 1
    assert "agenthub_http_request_duration_seconds_bucket" in text


def test_metrics_count_audit_events_and_database_state(client: TestClient) -> None:
    metric, event = "agenthub_audit_events_total", "AUTH_REGISTER_SUCCESS"
    before = _metric_value(client.get("/metrics").text, metric, event_type=event)
    register(client, USER)

    text = client.get("/metrics").text
    after = _metric_value(text, metric, event_type=event)
    assert after == before + 1
    assert re.search(r"^agenthub_users \d", text, re.MULTILINE)
    assert re.search(r"^agenthub_agent_skills_active \d", text, re.MULTILINE)


def test_metrics_token_protects_endpoint(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(settings, "metrics_token", SecretStr("segredo-de-teste"))

    assert client.get("/metrics").status_code == 401
    assert client.get("/metrics", headers={"Authorization": "Bearer errado"}).status_code == 401
    assert client.get("/metrics", headers={"Authorization": "Bearer segredo-de-teste"}).status_code == 200


def test_metrics_not_in_public_api_docs(client: TestClient) -> None:
    assert "/metrics" not in client.get("/openapi.json").json()["paths"]
