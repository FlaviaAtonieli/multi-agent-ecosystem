from fastapi.testclient import TestClient

from app.services import agent_skill_orchestration_service as service
from tests.conftest import authenticated_csrf_headers, create_qualified_request, register
from tests.test_background_orchestration import _fake_skill_tool
from tests.test_human_review import FIXTURE_MANIFEST

USER = {
    "name": "Contadora Teste",
    "email": "contadora.teste@example.com",
    "password": "StrongPassword!123",
}


def _create_skill(client: TestClient, domain: str, name: str = "Skill de Impostos"):
    return client.post(
        "/api/v1/agent-skills",
        json={
            "name": name,
            "version": "1.0",
            "author_origin": "Escritório Contábil",
            "domain": domain,
            "objective": "Avaliar o impacto fiscal de uma mudança.",
            "persona_instructions": "Você é especialista em contabilidade tributária.",
            "capabilities": ["Avaliar impostos"],
            "expected_inputs": ["Contexto da solicitação"],
            "produced_outputs": ["Riscos fiscais"],
            "operating_limits": ["Não substitui o contador responsável"],
            "input_contract_ref": "solicitacao_analise_schema.v1",
            "output_contract_ref": "resposta_especialista_schema.v1",
            "validation_criteria": ["Contrato válido"],
        },
        headers=authenticated_csrf_headers(client),
    )


def test_skill_can_declare_any_area(client: TestClient) -> None:
    register(client, USER)

    response = _create_skill(client, "  Folha   de Pagamento ")

    assert response.status_code == 201
    assert response.json()["domain"] == "Folha de Pagamento"


def test_spellings_of_the_same_area_are_unified(client: TestClient) -> None:
    register(client, USER)

    first = _create_skill(client, "Contabilidade", name="Skill de Impostos")
    second = _create_skill(client, "CONTABILIDADE", name="Skill de Balanços")
    accented = _create_skill(client, "Licitações", name="Skill de Editais")
    unaccented = _create_skill(client, "licitacoes", name="Skill de Contratos")

    assert first.json()["domain"] == second.json()["domain"] == "Contabilidade"
    assert accented.json()["domain"] == unaccented.json()["domain"] == "Licitações"


def test_catalog_spellings_keep_their_domain(client: TestClient) -> None:
    register(client, USER)

    for spelling in ["Dados e Privacidade (LGPD)", "lgpd", "dados_privacidade"]:
        response = _create_skill(client, spelling, name=f"Skill {spelling}")
        assert response.json()["domain"] == "dados_privacidade"


def test_area_has_length_limits(client: TestClient) -> None:
    register(client, USER)

    assert _create_skill(client, "x").status_code == 422
    assert _create_skill(client, "x" * 61).status_code == 422


def test_manifest_import_accepts_any_area(client: TestClient) -> None:
    register(client, USER)
    manifest = FIXTURE_MANIFEST.replace("Domínio de atuação: Código Legado", "Domínio de atuação: Jurídico")

    response = client.post(
        "/api/v1/agent-skills/import",
        json={"manifest_markdown": manifest},
        headers=authenticated_csrf_headers(client),
    )

    assert response.status_code == 201
    assert response.json()["domain"] == "Jurídico"


def test_request_runs_only_the_skills_of_the_chosen_area(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(service, "call_skill_tool", _fake_skill_tool)
    register(client, USER)
    _create_skill(client, "Contabilidade", name="Skill de Impostos")
    _create_skill(client, "Jurídico", name="Skill de Contratos")

    # Outra grafia na solicitação ainda encontra a área cadastrada.
    technical_request = create_qualified_request(client, requested_domains=["contabilidade"])
    response = client.post(
        f"/api/v1/agent-skills/requests/{technical_request['id']}/execute",
        headers=authenticated_csrf_headers(client),
    )

    assert response.status_code == 200
    results = response.json()["results"]
    assert [result["agente_emissor"]["dominio"] for result in results] == ["Contabilidade"]
