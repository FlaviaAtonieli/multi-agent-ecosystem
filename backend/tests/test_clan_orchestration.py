from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.db.seed_agent_skills import seed_agent_skills
from app.services import agent_skill_orchestration_service as service
from tests.conftest import authenticated_csrf_headers, csrf_headers, register
from tests.test_background_orchestration import _fake_skill_tool, _start_url, _wait_for_status
from tests.test_human_review import FIXTURE_MANIFEST

OWNER = {"name": "Dona do Cla", "email": "dona.cla@example.com", "password": "StrongPassword!123"}
OTHER = {"name": "Outra Pessoa", "email": "outra.cla@example.com", "password": "StrongPassword!123"}
CONTEXT = "O sistema legado calcula o limite de crédito de forma fixa e isso precisa mudar com segurança."


def _headers(client: TestClient) -> dict[str, str]:
    return authenticated_csrf_headers(client)


def _switch_user(client: TestClient, user: dict) -> None:
    client.post("/api/v1/auth/logout", headers=_headers(client))
    response = client.post(
        "/api/v1/auth/login",
        json={"email": user["email"], "password": user["password"]},
        headers=csrf_headers(client),
    )
    if response.status_code != 200:
        register(client, user)


def _skill(client: TestClient, domain: str, *, visibility: str = "OFFICIAL") -> dict:
    manifest = FIXTURE_MANIFEST.replace("Domínio de atuação: Código Legado", f"Domínio de atuação: {domain}")
    response = client.post(
        "/api/v1/agent-skills/import",
        json={"manifest_markdown": manifest, "visibility": visibility},
        headers=_headers(client),
    )
    assert response.status_code == 201, response.text
    return response.json()


def _clan(client: TestClient, **settings) -> dict:
    response = client.post(
        "/api/v1/clans", json={"name": f"Comitê {uuid4().hex[:8]}", **settings}, headers=_headers(client)
    )
    assert response.status_code == 201, response.text
    return response.json()


def _add(client: TestClient, clan_id: str, skill_id: str):
    return client.post(
        f"/api/v1/clans/{clan_id}/skills", json={"agent_skill_id": skill_id}, headers=_headers(client)
    )


def _request_payload(clan_id: str | None, domains: list[str] | None = None) -> dict:
    payload = {
        "title": "Avaliar limite de crédito",
        "problem": "O limite de crédito é global e precisa considerar o segmento.",
        "objective": "Gerar um plano técnico.",
        "context": CONTEXT,
        "restrictions": [],
        "requested_domains": domains or [],
    }
    if clan_id is not None:
        payload["clan_id"] = clan_id
    return payload


def _create_request(client: TestClient, clan_id: str, domains: list[str] | None = None) -> dict:
    response = client.post(
        "/api/v1/requests", json=_request_payload(clan_id, domains), headers=_headers(client)
    )
    assert response.status_code == 201, response.text
    return response.json()


def _run(client: TestClient, monkeypatch: pytest.MonkeyPatch, technical_request: dict) -> list[str]:
    """Executa e devolve as áreas das skills que foram chamadas de verdade."""
    called: list[str] = []

    async def spy(skill, tool_call):
        called.append(skill.domain)
        return await _fake_skill_tool(skill, tool_call)

    monkeypatch.setattr(service, "call_skill_tool", spy)
    response = client.post(_start_url(technical_request["id"]), headers=_headers(client))
    assert response.status_code == 202, response.text
    _wait_for_status(client, technical_request["id"], "COMPLETED", "VALIDATING")
    return called


class TestRequestNeedsClan:
    def test_request_without_clan_is_rejected(self, client: TestClient) -> None:
        register(client, OWNER)

        response = client.post("/api/v1/requests", json=_request_payload(None), headers=_headers(client))

        assert response.status_code == 422

    def test_request_keeps_the_chosen_clan(self, client: TestClient) -> None:
        register(client, OWNER)
        clan = _clan(client)

        assert _create_request(client, clan["id"])["clan_id"] == clan["id"]

    def test_unknown_clan_is_rejected(self, client: TestClient) -> None:
        register(client, OWNER)

        response = client.post(
            "/api/v1/requests", json=_request_payload("nao-existe"), headers=_headers(client)
        )

        assert response.status_code == 404

    def test_clan_of_someone_else_is_rejected(self, client: TestClient) -> None:
        register(client, OWNER)
        clan = _clan(client)
        _switch_user(client, OTHER)

        response = client.post(
            "/api/v1/requests", json=_request_payload(clan["id"]), headers=_headers(client)
        )

        assert response.status_code == 403


class TestExecutionUsesOnlyTheClan:
    def test_skills_outside_the_clan_are_not_called(self, client: TestClient, monkeypatch) -> None:
        register(client, OWNER)
        inside = _skill(client, "codigo_legado")
        _skill(client, "regras_negocio")
        clan = _clan(client)
        assert _add(client, clan["id"], inside["id"]).status_code == 201

        assert _run(client, monkeypatch, _create_request(client, clan["id"])) == ["codigo_legado"]

    def test_chosen_areas_narrow_the_clan(self, client: TestClient, monkeypatch) -> None:
        register(client, OWNER)
        clan = _clan(client)
        for domain in ["codigo_legado", "regras_negocio"]:
            _add(client, clan["id"], _skill(client, domain)["id"])

        request = _create_request(client, clan["id"], ["regras_negocio"])

        assert _run(client, monkeypatch, request) == ["regras_negocio"]

    def test_chosen_area_outside_the_clan_does_not_run(self, client: TestClient) -> None:
        register(client, OWNER)
        _skill(client, "regras_negocio")
        clan = _clan(client)
        _add(client, clan["id"], _skill(client, "codigo_legado")["id"])

        request = _create_request(client, clan["id"], ["regras_negocio"])
        response = client.post(_start_url(request["id"]), headers=_headers(client))

        assert response.status_code == 409

    def test_clan_without_skills_cannot_run(self, client: TestClient) -> None:
        register(client, OWNER)
        _skill(client, "codigo_legado")
        clan = _clan(client)

        request = _create_request(client, clan["id"])
        response = client.post(_start_url(request["id"]), headers=_headers(client))

        assert response.status_code == 409

    def test_disabled_skill_in_the_clan_does_not_run(self, client: TestClient) -> None:
        register(client, OWNER)
        skill = _skill(client, "codigo_legado")
        clan = _clan(client)
        _add(client, clan["id"], skill["id"])
        client.patch(f"/api/v1/agent-skills/{skill['id']}/disable", headers=_headers(client))

        request = _create_request(client, clan["id"])
        response = client.post(_start_url(request["id"]), headers=_headers(client))

        assert response.status_code == 409

    def test_person_removed_from_the_clan_cannot_run_its_request(self, client: TestClient) -> None:
        register(client, OWNER)
        skill = _skill(client, "codigo_legado")
        clan = _clan(client, is_open=True)
        _add(client, clan["id"], skill["id"])
        _switch_user(client, OTHER)
        client.post(f"/api/v1/clans/{clan['id']}/join", headers=_headers(client))
        request = _create_request(client, clan["id"])
        other_id = client.get("/api/v1/auth/me").json()["id"]
        _switch_user(client, OWNER)
        removed = client.delete(f"/api/v1/clans/{clan['id']}/members/{other_id}", headers=_headers(client))
        assert removed.status_code == 200, removed.text
        _switch_user(client, OTHER)

        response = client.post(_start_url(request["id"]), headers=_headers(client))

        assert response.status_code == 409

    def test_member_runs_private_skill_shared_in_the_clan(self, client: TestClient, monkeypatch) -> None:
        register(client, OWNER)
        private = _skill(client, "codigo_legado", visibility="PRIVATE")
        clan = _clan(client, is_open=True)
        _add(client, clan["id"], private["id"])
        _switch_user(client, OTHER)
        client.post(f"/api/v1/clans/{clan['id']}/join", headers=_headers(client))

        assert _run(client, monkeypatch, _create_request(client, clan["id"])) == ["codigo_legado"]


class TestSkillsInClan:
    def test_published_skill_of_someone_else_can_be_added(self, client: TestClient) -> None:
        register(client, OWNER)
        skill = _skill(client, "codigo_legado")
        _switch_user(client, OTHER)
        clan = _clan(client)

        assert _add(client, clan["id"], skill["id"]).status_code == 201
        listed = client.get(f"/api/v1/clans/{clan['id']}/skills").json()
        assert [item["id"] for item in listed] == [skill["id"]]

    def test_same_skill_can_be_in_several_clans(self, client: TestClient) -> None:
        register(client, OWNER)
        skill = _skill(client, "codigo_legado")

        assert _add(client, _clan(client)["id"], skill["id"]).status_code == 201
        assert _add(client, _clan(client)["id"], skill["id"]).status_code == 201

    def test_private_skill_of_someone_else_cannot_be_added(self, client: TestClient) -> None:
        register(client, OWNER)
        private = _skill(client, "codigo_legado", visibility="PRIVATE")
        _switch_user(client, OTHER)
        clan = _clan(client)

        assert _add(client, clan["id"], private["id"]).status_code == 404

    def test_adding_twice_is_a_conflict(self, client: TestClient) -> None:
        register(client, OWNER)
        skill = _skill(client, "codigo_legado")
        clan = _clan(client)
        _add(client, clan["id"], skill["id"])

        assert _add(client, clan["id"], skill["id"]).status_code == 409

    def test_non_member_cannot_add(self, client: TestClient) -> None:
        register(client, OWNER)
        skill = _skill(client, "codigo_legado")
        clan = _clan(client)
        _switch_user(client, OTHER)

        assert _add(client, clan["id"], skill["id"]).status_code == 403

    def test_owner_only_policy_blocks_other_members(self, client: TestClient) -> None:
        register(client, OWNER)
        skill = _skill(client, "codigo_legado")
        clan = _clan(client, is_open=True, skills_policy="OWNER_ONLY")
        _switch_user(client, OTHER)
        client.post(f"/api/v1/clans/{clan['id']}/join", headers=_headers(client))

        assert _add(client, clan["id"], skill["id"]).status_code == 403

    def test_skill_can_be_removed_from_the_clan(self, client: TestClient) -> None:
        register(client, OWNER)
        skill = _skill(client, "codigo_legado")
        clan = _clan(client)
        _add(client, clan["id"], skill["id"])

        response = client.delete(f"/api/v1/clans/{clan['id']}/skills/{skill['id']}", headers=_headers(client))

        assert response.status_code == 204
        assert client.get(f"/api/v1/clans/{clan['id']}/skills").json() == []

    def test_closed_clan_skills_are_hidden_from_non_members(self, client: TestClient) -> None:
        register(client, OWNER)
        clan = _clan(client)
        _switch_user(client, OTHER)

        assert client.get(f"/api/v1/clans/{clan['id']}/skills").status_code == 403

    def test_open_clan_skills_are_visible_before_joining(self, client: TestClient) -> None:
        register(client, OWNER)
        clan = _clan(client, is_open=True)
        _switch_user(client, OTHER)

        assert client.get(f"/api/v1/clans/{clan['id']}/skills").status_code == 200

    def test_skill_created_for_a_clan_is_already_in_it(self, client: TestClient) -> None:
        register(client, OWNER)
        clan = _clan(client)
        manifest = FIXTURE_MANIFEST
        created = client.post(
            "/api/v1/agent-skills/import",
            json={"manifest_markdown": manifest, "visibility": "CLAN", "clan_id": clan["id"]},
            headers=_headers(client),
        )
        assert created.status_code == 201, created.text

        listed = client.get(f"/api/v1/clans/{clan['id']}/skills").json()
        assert [item["id"] for item in listed] == [created.json()["id"]]


class TestFollowUp:
    def _completed(self, client: TestClient, monkeypatch) -> dict:
        register(client, OWNER)
        _skill(client, "regras_negocio")
        clan = _clan(client)
        _add(client, clan["id"], _skill(client, "codigo_legado")["id"])
        request = _create_request(client, clan["id"])
        _run(client, monkeypatch, request)
        return request

    def test_question_cannot_reach_area_outside_the_clan(self, client: TestClient, monkeypatch) -> None:
        request = self._completed(client, monkeypatch)

        response = client.post(
            f"/api/v1/agent-skills/requests/{request['id']}/ask/start",
            json={"question": "Qual é o maior risco?", "target_domain": "regras_negocio"},
            headers=_headers(client),
        )

        assert response.status_code == 409

    def test_question_reaches_area_inside_the_clan(self, client: TestClient, monkeypatch) -> None:
        request = self._completed(client, monkeypatch)

        response = client.post(
            f"/api/v1/agent-skills/requests/{request['id']}/ask/start",
            json={"question": "Qual é o maior risco?", "target_domain": "codigo_legado"},
            headers=_headers(client),
        )

        assert response.status_code == 202


class TestEcosystemClan:
    def test_seed_creates_open_clan_with_official_skills_only_once(
        self, client: TestClient, monkeypatch
    ) -> None:
        register(client, OWNER)
        monkeypatch.setattr(settings, "bootstrap_admin_email", OWNER["email"])
        published = _skill(client, "Contabilidade")

        seed_agent_skills()
        seed_agent_skills()

        clans = client.get("/api/v1/clans").json()
        ecosystem = [clan for clan in clans if clan["name"] == "Ecossistema"]
        assert len(ecosystem) == 1
        assert ecosystem[0]["is_open"] is True
        skills = client.get(f"/api/v1/clans/{ecosystem[0]['id']}/skills").json()
        assert len(skills) == 10
        assert published["id"] not in [skill["id"] for skill in skills]

    def test_new_person_joins_and_runs_with_official_skills(self, client: TestClient, monkeypatch) -> None:
        register(client, OWNER)
        monkeypatch.setattr(settings, "bootstrap_admin_email", OWNER["email"])
        seed_agent_skills()
        _switch_user(client, OTHER)
        clan = next(item for item in client.get("/api/v1/clans").json() if item["name"] == "Ecossistema")

        assert client.post(f"/api/v1/clans/{clan['id']}/join", headers=_headers(client)).status_code == 200

        request = _create_request(client, clan["id"], ["codigo_legado"])
        assert _run(client, monkeypatch, request) == ["codigo_legado"]
