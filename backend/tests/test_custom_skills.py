from fastapi.testclient import TestClient

from tests.conftest import (
    authenticated_csrf_headers,
    create_qualified_request,
    enable_real_llm,
    register,
)

OWNER = {
    "name": "Dona da Skill",
    "email": "dona.skill@example.com",
    "password": "StrongPassword!123",
}
OTHER_USER = {
    "name": "Outra Usuaria",
    "email": "outra.usuaria@example.com",
    "password": "StrongPassword!123",
}

CUSTOM_SKILL_PAYLOAD = {
    "name": "Revisor Cauteloso de Código Legado",
    "version": "1.0",
    "author_origin": "Dona da Skill",
    "domain": "codigo_legado",
    "objective": "Revisar código legado com foco extra em regressões silenciosas.",
    "capabilities": ["Apontar riscos de regressão silenciosa"],
    "expected_inputs": ["Contexto técnico da solicitação"],
    "produced_outputs": ["Riscos de regressão priorizados"],
    "operating_limits": ["Não executa nem altera código"],
    "input_contract_ref": "solicitacao_analise_schema.v1",
    "output_contract_ref": "resposta_especialista_schema.v1",
    "validation_criteria": ["Cada risco citado precisa de justificativa"],
    "persona_instructions": (
        "Você é extremamente cauteloso: para cada mudança sugerida, pergunte "
        "explicitamente 'o que pode quebrar silenciosamente' antes de concluir."
    ),
}


def _create_custom_skill(client: TestClient) -> dict:
    response = client.post(
        "/api/v1/agent-skills",
        json=CUSTOM_SKILL_PAYLOAD,
        headers=authenticated_csrf_headers(client),
    )
    assert response.status_code == 201
    return response.json()


def test_custom_skill_is_official_and_visible_to_everyone(client: TestClient) -> None:
    """New skills default to OFFICIAL (not PRIVATE) so the catalog isn't empty
    for anyone besides whichever TECHNICIAN/ADMIN happened to import each one
    -- a plain USER, allowed to execute orchestrations (ORCHESTRATION_ROLES),
    needs something to actually run. owner_id is still recorded for
    attribution even though it no longer gates visibility."""
    register(client, OWNER)
    skill = _create_custom_skill(client)
    assert skill["owner_id"] is not None
    assert skill["visibility"] == "OFFICIAL"

    owner_catalog = client.get("/api/v1/agent-skills").json()
    assert any(item["id"] == skill["id"] for item in owner_catalog)

    owner_detail = client.get(f"/api/v1/agent-skills/{skill['id']}")
    assert owner_detail.status_code == 200

    client.post("/api/v1/auth/logout", headers=authenticated_csrf_headers(client))
    register(client, OTHER_USER)

    other_catalog = client.get("/api/v1/agent-skills").json()
    assert any(item["id"] == skill["id"] for item in other_catalog)

    other_detail = client.get(f"/api/v1/agent-skills/{skill['id']}")
    assert other_detail.status_code == 200


def test_generic_executor_runs_custom_skill_end_to_end(client: TestClient, monkeypatch) -> None:
    register(client, OWNER)
    skill = _create_custom_skill(client)

    technical_request = create_qualified_request(client, requested_domains=["codigo_legado"])

    enable_real_llm(monkeypatch)

    execution_response = client.post(
        f"/api/v1/agent-skills/requests/{technical_request['id']}/execute",
        headers=authenticated_csrf_headers(client),
    )
    assert execution_response.status_code == 200
    payload = execution_response.json()
    assert payload["invocations_count"] == 1
    result = payload["results"][0]
    assert result["agente_emissor"]["nome"] == skill["name"]
    assert result["agente_emissor"]["dominio"] == "codigo_legado"
    assert result["analise_estruturada"]["resumo_executivo"]
    assert result["governanca"]["nivel_confianca"] in {"ALTO", "MEDIO", "BAIXO"}


def test_plain_user_can_execute_orchestration_on_others_official_skill(
    client: TestClient, monkeypatch
) -> None:
    """The actual end-to-end goal of opening execution up to USER: a plain
    USER (never promoted) creates their own request and runs it against a
    skill a TECHNICIAN imported -- no role beyond being logged in, and no
    ownership of the skill itself, required."""
    register(client, OWNER)
    _create_custom_skill(client)

    client.post("/api/v1/auth/logout", headers=authenticated_csrf_headers(client))
    register(client, OTHER_USER)  # stays USER -- never promoted

    technical_request = create_qualified_request(client, requested_domains=["codigo_legado"])

    enable_real_llm(monkeypatch)

    execution_response = client.post(
        f"/api/v1/agent-skills/requests/{technical_request['id']}/execute",
        headers=authenticated_csrf_headers(client),
    )
    assert execution_response.status_code == 200
    payload = execution_response.json()
    assert payload["invocations_count"] == 1
    assert len(payload["results"]) == 1


def test_owner_can_update_and_disable_own_skill(client: TestClient) -> None:
    register(client, OWNER)
    skill = _create_custom_skill(client)

    updated = client.put(
        f"/api/v1/agent-skills/{skill['id']}",
        json={**CUSTOM_SKILL_PAYLOAD, "version": "1.1", "objective": "Objetivo revisado com mais detalhes."},
        headers=authenticated_csrf_headers(client),
    )
    assert updated.status_code == 200
    assert updated.json()["id"] == skill["id"]  # editado no lugar, mesmo id
    assert updated.json()["version"] == "1.1"
    assert updated.json()["objective"] == "Objetivo revisado com mais detalhes."

    disabled = client.patch(
        f"/api/v1/agent-skills/{skill['id']}/disable", headers=authenticated_csrf_headers(client)
    )
    assert disabled.status_code == 200
    assert disabled.json()["enabled"] is False


def test_update_rejects_invalid_manifest(client: TestClient) -> None:
    register(client, OWNER)
    skill = _create_custom_skill(client)

    response = client.put(
        f"/api/v1/agent-skills/{skill['id']}",
        json={**CUSTOM_SKILL_PAYLOAD, "capabilities": [], "validation_criteria": []},
        headers=authenticated_csrf_headers(client),
    )
    assert response.status_code == 422


def test_other_user_cannot_update_or_disable_skill(client: TestClient) -> None:
    register(client, OWNER)
    skill = _create_custom_skill(client)

    client.post("/api/v1/auth/logout", headers=authenticated_csrf_headers(client))
    register(client, OTHER_USER)

    update = client.put(
        f"/api/v1/agent-skills/{skill['id']}",
        json={**CUSTOM_SKILL_PAYLOAD, "version": "9.9"},
        headers=authenticated_csrf_headers(client),
    )
    assert update.status_code == 403

    disable = client.patch(
        f"/api/v1/agent-skills/{skill['id']}/disable", headers=authenticated_csrf_headers(client)
    )
    assert disable.status_code == 403
