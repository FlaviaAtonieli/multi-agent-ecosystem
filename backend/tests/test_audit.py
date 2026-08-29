from fastapi.testclient import TestClient

from tests.conftest import authenticated_csrf_headers, create_qualified_request, promote, register

OWNER = {
    "name": "Dono da Solicitacao",
    "email": "dono.solicitacao@example.com",
    "password": "StrongPassword!123",
}
AUDITOR = {
    "name": "Auditora Reviewer",
    "email": "auditora.reviewer@example.com",
    "password": "StrongPassword!123",
}


def test_audit_events_requires_reviewer_or_admin_role(client: TestClient) -> None:
    register(client, OWNER)
    create_qualified_request(client)

    response = client.get("/api/v1/audit/events")
    assert response.status_code == 403


def test_audit_events_lists_events_across_users(client: TestClient) -> None:
    register(client, OWNER)
    technical_request = create_qualified_request(client, title="Investigar timeout no checkout")

    client.post("/api/v1/auth/logout", headers=authenticated_csrf_headers(client))
    register(client, AUDITOR)
    promote(AUDITOR["email"], "REVIEWER")

    response = client.get("/api/v1/audit/events", headers=authenticated_csrf_headers(client))
    assert response.status_code == 200
    payload = response.json()

    matching = [item for item in payload["items"] if item["request_id"] == technical_request["id"]]
    assert len(matching) >= 1
    assert matching[0]["request_title"] == "Investigar timeout no checkout"
    assert matching[0]["request_trace_id"] == technical_request["trace_id"]
    event_types = {item["event_type"] for item in matching}
    assert "REQUEST_CREATED" in event_types

    assert payload["stats"]["events_today"] >= len(matching)
    assert payload["stats"]["manual_interventions_today"] >= 1


def test_audit_events_filters_by_actor(client: TestClient) -> None:
    register(client, OWNER)
    create_qualified_request(client)

    client.post("/api/v1/auth/logout", headers=authenticated_csrf_headers(client))
    register(client, AUDITOR)
    promote(AUDITOR["email"], "REVIEWER")

    response = client.get(
        "/api/v1/audit/events", params={"actor": "USER"}, headers=authenticated_csrf_headers(client)
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["items"]
    assert all(item["actor"] == "USER" for item in payload["items"])


def test_audit_events_filters_by_search(client: TestClient) -> None:
    register(client, OWNER)
    technical_request = create_qualified_request(client, title="Corrigir vazamento de memória no worker")

    client.post("/api/v1/auth/logout", headers=authenticated_csrf_headers(client))
    register(client, AUDITOR)
    promote(AUDITOR["email"], "REVIEWER")

    response = client.get(
        "/api/v1/audit/events",
        params={"search": technical_request["trace_id"]},
        headers=authenticated_csrf_headers(client),
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["items"]
    assert all(item["request_trace_id"] == technical_request["trace_id"] for item in payload["items"])

    empty_response = client.get(
        "/api/v1/audit/events",
        params={"search": "nao existe nenhuma solicitacao com este termo"},
        headers=authenticated_csrf_headers(client),
    )
    assert empty_response.json()["items"] == []
