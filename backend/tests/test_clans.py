from pathlib import Path

from fastapi.testclient import TestClient

from tests.conftest import authenticated_csrf_headers, csrf_headers, promote, register

ALICE = {"name": "Alice Criadora", "email": "alice.cla@example.com", "password": "StrongPassword!123"}
BOB = {"name": "Bob Convidado", "email": "bob.cla@example.com", "password": "StrongPassword!123"}
CARLA = {"name": "Carla De Fora", "email": "carla.cla@example.com", "password": "StrongPassword!123"}
ADMIN = {"name": "Admin Cla", "email": "admin.cla@example.com", "password": "StrongPassword!123"}

LEGACY_CODE_FIXTURE_MANIFEST = (
    Path(__file__).resolve().parent.parent / "app" / "agent_manifest" / "fixtures" / "legacy-code-skill.md"
).read_text(encoding="utf-8")


def _login(client: TestClient, user: dict) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": user["email"], "password": user["password"]},
        headers=csrf_headers(client),
    )
    assert response.status_code == 200


def _create_clan(client: TestClient, name: str = "Time Backend") -> dict:
    response = client.post(
        "/api/v1/clans", json={"name": name}, headers=authenticated_csrf_headers(client)
    )
    assert response.status_code == 201
    return response.json()


def test_create_clan_auto_joins_creator(client: TestClient) -> None:
    register(client, ALICE)
    clan = _create_clan(client)

    assert clan["name"] == "Time Backend"
    assert len(clan["members"]) == 1
    assert clan["members"][0]["email"] == ALICE["email"]


def test_create_clan_duplicate_name_conflicts(client: TestClient) -> None:
    register(client, ALICE)
    _create_clan(client, "Time Único")

    response = client.post(
        "/api/v1/clans", json={"name": "Time Único"}, headers=authenticated_csrf_headers(client)
    )
    assert response.status_code == 409


def test_member_can_add_and_remove_another_user(client: TestClient) -> None:
    register(client, ALICE)
    clan = _create_clan(client)

    client.post("/api/v1/auth/logout", headers=authenticated_csrf_headers(client))
    register(client, BOB)
    client.post("/api/v1/auth/logout", headers=authenticated_csrf_headers(client))

    _login(client, ALICE)
    add_response = client.post(
        f"/api/v1/clans/{clan['id']}/members",
        json={"email": BOB["email"]},
        headers=authenticated_csrf_headers(client),
    )
    assert add_response.status_code == 201
    emails = {m["email"] for m in add_response.json()["members"]}
    assert BOB["email"] in emails

    bob_id = next(m["user_id"] for m in add_response.json()["members"] if m["email"] == BOB["email"])
    remove_response = client.delete(
        f"/api/v1/clans/{clan['id']}/members/{bob_id}", headers=authenticated_csrf_headers(client)
    )
    assert remove_response.status_code == 200
    assert BOB["email"] not in {m["email"] for m in remove_response.json()["members"]}


def test_non_member_cannot_add_to_clan(client: TestClient) -> None:
    register(client, ALICE)
    clan = _create_clan(client)

    client.post("/api/v1/auth/logout", headers=authenticated_csrf_headers(client))
    register(client, BOB)  # must exist for the add-member call to reach the membership check

    client.post("/api/v1/auth/logout", headers=authenticated_csrf_headers(client))
    register(client, CARLA)

    response = client.post(
        f"/api/v1/clans/{clan['id']}/members",
        json={"email": BOB["email"]},
        headers=authenticated_csrf_headers(client),
    )
    assert response.status_code == 403


def test_admin_can_manage_any_clan_without_membership(client: TestClient) -> None:
    register(client, ALICE)
    clan = _create_clan(client)

    client.post("/api/v1/auth/logout", headers=authenticated_csrf_headers(client))
    register(client, BOB)
    client.post("/api/v1/auth/logout", headers=authenticated_csrf_headers(client))

    register(client, ADMIN)
    promote(ADMIN["email"], "ADMIN")

    response = client.post(
        f"/api/v1/clans/{clan['id']}/members",
        json={"email": BOB["email"]},
        headers=authenticated_csrf_headers(client),
    )
    assert response.status_code == 201
    assert BOB["email"] in {m["email"] for m in response.json()["members"]}


def test_clan_skill_visible_only_to_members(client: TestClient) -> None:
    fixture = LEGACY_CODE_FIXTURE_MANIFEST

    register(client, ALICE)
    promote(ALICE["email"], "TECHNICIAN")
    clan = _create_clan(client, "Time Legado")

    create_response = client.post(
        "/api/v1/agent-skills/import",
        json={"manifest_markdown": fixture, "visibility": "CLAN", "clan_id": clan["id"]},
        headers=authenticated_csrf_headers(client),
    )
    assert create_response.status_code == 201
    skill_id = create_response.json()["id"]
    assert create_response.json()["visibility"] == "CLAN"
    assert create_response.json()["clan_id"] == clan["id"]

    # Alice (member) sees it in her catalog listing.
    listing = client.get("/api/v1/agent-skills?only_active=false", headers=authenticated_csrf_headers(client))
    assert any(item["id"] == skill_id for item in listing.json())

    client.post("/api/v1/auth/logout", headers=authenticated_csrf_headers(client))
    register(client, CARLA)  # never joined the clan

    outsider_listing = client.get(
        "/api/v1/agent-skills?only_active=false", headers=authenticated_csrf_headers(client)
    )
    assert all(item["id"] != skill_id for item in outsider_listing.json())

    outsider_detail = client.get(
        f"/api/v1/agent-skills/{skill_id}", headers=authenticated_csrf_headers(client)
    )
    assert outsider_detail.status_code == 404

    client.post("/api/v1/auth/logout", headers=authenticated_csrf_headers(client))
    register(client, BOB)
    client.post("/api/v1/auth/logout", headers=authenticated_csrf_headers(client))
    _login(client, ALICE)
    client.post(
        f"/api/v1/clans/{clan['id']}/members",
        json={"email": BOB["email"]},
        headers=authenticated_csrf_headers(client),
    )

    client.post("/api/v1/auth/logout", headers=authenticated_csrf_headers(client))
    _login(client, BOB)
    member_listing = client.get(
        "/api/v1/agent-skills?only_active=false", headers=authenticated_csrf_headers(client)
    )
    assert any(item["id"] == skill_id for item in member_listing.json())


def test_creating_clan_skill_requires_membership(client: TestClient) -> None:
    fixture = LEGACY_CODE_FIXTURE_MANIFEST

    register(client, ALICE)
    promote(ALICE["email"], "TECHNICIAN")
    clan = _create_clan(client, "Time Sem Bob")

    client.post("/api/v1/auth/logout", headers=authenticated_csrf_headers(client))
    register(client, BOB)
    promote(BOB["email"], "TECHNICIAN")

    response = client.post(
        "/api/v1/agent-skills/import",
        json={"manifest_markdown": fixture, "visibility": "CLAN", "clan_id": clan["id"]},
        headers=authenticated_csrf_headers(client),
    )
    assert response.status_code == 403


def test_creating_clan_skill_without_clan_id_is_422(client: TestClient) -> None:
    fixture = LEGACY_CODE_FIXTURE_MANIFEST

    register(client, ALICE)
    promote(ALICE["email"], "TECHNICIAN")

    response = client.post(
        "/api/v1/agent-skills/import",
        json={"manifest_markdown": fixture, "visibility": "CLAN"},
        headers=authenticated_csrf_headers(client),
    )
    assert response.status_code == 422
