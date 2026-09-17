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


def test_audit_events_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/audit/events")
    assert response.status_code == 401


def test_audit_events_scopes_plain_user_to_own_requests(client: TestClient) -> None:
    """Any authenticated role (USER included) can open the audit trail, but
    without REVIEWER/ADMIN it's scoped to requests the caller owns."""
    register(client, OWNER)
    technical_request = create_qualified_request(client, title="Investigar timeout no checkout")

    response = client.get("/api/v1/audit/events", headers=authenticated_csrf_headers(client))
    assert response.status_code == 200
    payload = response.json()

    matching = [item for item in payload["items"] if item["request_id"] == technical_request["id"]]
    assert len(matching) >= 1
    event_types = {item["event_type"] for item in matching}
    assert "REQUEST_CREATED" in event_types
    assert payload["stats"]["events_today"] >= len(matching)


def test_audit_events_plain_user_cannot_see_others_requests(client: TestClient) -> None:
    register(client, OWNER)
    technical_request = create_qualified_request(client, title="Investigar timeout no checkout")

    client.post("/api/v1/auth/logout", headers=authenticated_csrf_headers(client))
    register(client, AUDITOR)  # a second plain USER account, not promoted here

    response = client.get("/api/v1/audit/events", headers=authenticated_csrf_headers(client))
    assert response.status_code == 200
    payload = response.json()

    assert all(item["request_id"] != technical_request["id"] for item in payload["items"])


def test_audit_events_plain_user_stat_counters_dont_leak_other_users(client: TestClient) -> None:
    """Amanda's review on #44: the list was proven scoped, but were the 4
    top-of-page counters (events_today, automated_decisions_today,
    manual_interventions_today, compliance_alerts_today) actually scoped too,
    or could they leak a system-wide count to a non-reviewer? Proves it by
    comparing a plain USER's counters against the true system-wide total
    (visible only to a REVIEWER) after a *different* user also generated
    events today -- if the USER's counters matched the total, they'd be
    leaking; instead every counter for the plain USER must equal exactly
    what their own items add up to, and be strictly less than the total."""
    register(client, OWNER)
    create_qualified_request(client, title="Solicitacao de outro usuario")

    client.post("/api/v1/auth/logout", headers=authenticated_csrf_headers(client))
    register(client, AUDITOR)  # stays a plain USER here, not promoted
    empty_response = client.get("/api/v1/audit/events", headers=authenticated_csrf_headers(client))
    assert empty_response.json()["stats"] == {
        "events_today": 0,
        "automated_decisions_today": 0,
        "manual_interventions_today": 0,
        "compliance_alerts_today": 0,
    }
    assert empty_response.json()["items"] == []

    create_qualified_request(client, title="Solicitacao da propria auditora")
    scoped_response = client.get(
        "/api/v1/audit/events", params={"limit": 200}, headers=authenticated_csrf_headers(client)
    )
    scoped_payload = scoped_response.json()
    scoped_stats = scoped_payload["stats"]

    # Every item this plain USER can see is necessarily their own (already
    # proven by test_audit_events_plain_user_cannot_see_others_requests) and
    # happened today, so events_today must equal the item count exactly --
    # not >=, which would also be true of a leaked system-wide count.
    assert scoped_stats["events_today"] == len(scoped_payload["items"])
    assert scoped_stats["manual_interventions_today"] >= 1

    third_party = {
        "name": "Revisora Independente",
        "email": "revisora.independente@example.com",
        "password": "StrongPassword!123",
    }
    client.post("/api/v1/auth/logout", headers=authenticated_csrf_headers(client))
    register(client, third_party)
    promote(third_party["email"], "REVIEWER")
    system_wide_stats = client.get(
        "/api/v1/audit/events", headers=authenticated_csrf_headers(client)
    ).json()["stats"]

    # The system-wide total (OWNER's events + AUDITOR's) must be strictly
    # greater than what AUDITOR alone saw -- if it weren't, AUDITOR's
    # "scoped" counters would actually have been the leaked total all along.
    assert system_wide_stats["events_today"] > scoped_stats["events_today"]
    assert system_wide_stats["manual_interventions_today"] > scoped_stats["manual_interventions_today"]


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
