from fastapi.testclient import TestClient

from tests.conftest import csrf_headers


USER = {
    "name": "Flavia Souza",
    "email": "flavia.orchestration@example.com",
    "password": "StrongPassword!123",
}


def authenticated_csrf_headers(client: TestClient) -> dict[str, str]:
    token = client.cookies.get("agenthub_csrf")
    assert token
    return {"X-CSRF-Token": token}


def test_orchestration_foundation_flow(client: TestClient) -> None:
    register_response = client.post(
        "/api/v1/auth/register",
        json=USER,
        headers=csrf_headers(client),
    )
    assert register_response.status_code == 201

    create_response = client.post(
        "/api/v1/requests",
        json={
            "title": "Analisar integração corporativa",
            "problem": "A API atual apresenta inconsistência entre contrato e retorno.",
            "objective": "Mapear o impacto técnico e orientar a correção.",
            "context": "Curto",
            "restrictions": ["Não alterar código automaticamente"],
        },
        headers=authenticated_csrf_headers(client),
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["status"] == "AWAITING_CONTEXT"
    assert created["trace_id"].startswith("TRC-")

    initial_detail = client.get(f"/api/v1/orchestrations/{created['trace_id']}")
    assert initial_detail.status_code == 200
    assert [event["event_type"] for event in initial_detail.json()["events"]] == [
        "REQUEST_CREATED",
        "CONTEXT_REQUESTED",
    ]

    update_response = client.post(
        f"/api/v1/requests/{created['id']}/context",
        json={
            "context": (
                "A integração ocorre entre o módulo de estoque e a API de compras. "
                "O retorno esperado contém oito sequências, mas apenas quatro são exibidas."
            )
        },
        headers=authenticated_csrf_headers(client),
    )
    assert update_response.status_code == 200
    assert update_response.json()["status"] == "QUALIFIED"

    final_detail = client.get(f"/api/v1/orchestrations/{created['trace_id']}")
    assert final_detail.status_code == 200
    assert [event["event_type"] for event in final_detail.json()["events"]] == [
        "REQUEST_CREATED",
        "CONTEXT_REQUESTED",
        "CONTEXT_PROVIDED",
        "CONTEXT_QUALIFIED",
    ]

    dashboard = client.get("/api/v1/dashboard/summary")
    assert dashboard.status_code == 200
    summary = dashboard.json()
    assert summary["orchestration_executions"] == 1
    assert summary["running_orchestrations"] == 1
    assert summary["awaiting_context"] == 0
    assert len(summary["recent_requests"]) == 1
    assert summary["recent_orchestration_events"][0]["event_type"] == "CONTEXT_QUALIFIED"
