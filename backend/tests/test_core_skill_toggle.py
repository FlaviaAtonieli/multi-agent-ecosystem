import pytest
from fastapi.testclient import TestClient

from app.agent_catalog.registry import register_skill
from app.agent_manifest.manifest import parse_modelo_md
from app.core.config import settings
from app.core.database import SessionLocal
from app.models import User
from tests.conftest import authenticated_csrf_headers, register, user_id_for
from tests.test_human_review import FIXTURE_MANIFEST

INITIAL = {
    "name": "Conta Inicial",
    "email": "conta.inicial@example.com",
    "password": "StrongPassword!123",
}
OTHER = {
    "name": "Outra Pessoa",
    "email": "outra.pessoa@example.com",
    "password": "StrongPassword!123",
}
SKILL_PAYLOAD = {
    "name": "Skill de Outra Pessoa",
    "version": "1.0",
    "author_origin": "Teste",
    "domain": "Contabilidade",
    "objective": "Avaliar o impacto fiscal de uma mudança.",
    "persona_instructions": "Você é especialista em tributos.",
    "capabilities": ["Avaliar impostos"],
    "expected_inputs": ["Contexto"],
    "produced_outputs": ["Riscos"],
    "operating_limits": ["Não substitui o contador"],
    "input_contract_ref": "solicitacao_analise_schema.v1",
    "output_contract_ref": "resposta_especialista_schema.v1",
    "validation_criteria": ["Contrato válido"],
}


@pytest.fixture(autouse=True)
def initial_account(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "bootstrap_admin_email", INITIAL["email"])


def _core_skill(owner_email: str) -> str:
    """Skill sem dono, como as 4 que a seed registra com servidor MCP próprio."""
    with SessionLocal() as db:
        skill = register_skill(
            db,
            manifest=parse_modelo_md(FIXTURE_MANIFEST),
            submitted_by=db.get(User, user_id_for(owner_email)),
            raw_markdown=FIXTURE_MANIFEST,
            owner_id=None,
            visibility="OFFICIAL",
        )
        db.commit()
        return skill.id


def _patch(client: TestClient, skill_id: str, action: str):
    return client.patch(
        f"/api/v1/agent-skills/{skill_id}/{action}", headers=authenticated_csrf_headers(client)
    )


def test_initial_account_can_disable_and_reenable_core_skill(client: TestClient) -> None:
    register(client, INITIAL)
    skill_id = _core_skill(INITIAL["email"])

    disabled = _patch(client, skill_id, "disable")
    assert disabled.status_code == 200
    assert disabled.json()["enabled"] is False

    active = client.get("/api/v1/agent-skills?only_active=true").json()
    assert skill_id not in [skill["id"] for skill in active]

    enabled = _patch(client, skill_id, "enable")
    assert enabled.status_code == 200
    assert enabled.json()["enabled"] is True


def test_toggle_does_not_change_which_server_runs_the_skill(client: TestClient) -> None:
    register(client, INITIAL)
    skill_id = _core_skill(INITIAL["email"])

    assert _patch(client, skill_id, "disable").json()["owner_id"] is None


def test_email_comparison_ignores_case(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "bootstrap_admin_email", "Conta.Inicial@Example.com")
    register(client, INITIAL)
    skill_id = _core_skill(INITIAL["email"])

    assert _patch(client, skill_id, "disable").status_code == 200


def test_initial_account_cannot_edit_core_skill(client: TestClient) -> None:
    register(client, INITIAL)
    skill_id = _core_skill(INITIAL["email"])

    response = client.put(
        f"/api/v1/agent-skills/{skill_id}",
        json=SKILL_PAYLOAD,
        headers=authenticated_csrf_headers(client),
    )

    assert response.status_code == 403


def test_other_user_cannot_toggle_core_skill(client: TestClient) -> None:
    register(client, INITIAL)
    skill_id = _core_skill(INITIAL["email"])
    client.post("/api/v1/auth/logout", headers=authenticated_csrf_headers(client))
    register(client, OTHER)

    assert _patch(client, skill_id, "disable").status_code == 403


def test_no_one_can_toggle_core_skill_without_configured_account(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "bootstrap_admin_email", "")
    register(client, INITIAL)
    skill_id = _core_skill(INITIAL["email"])

    assert _patch(client, skill_id, "disable").status_code == 403


def test_initial_account_cannot_toggle_skill_owned_by_someone_else(client: TestClient) -> None:
    register(client, OTHER)
    created = client.post(
        "/api/v1/agent-skills", json=SKILL_PAYLOAD, headers=authenticated_csrf_headers(client)
    ).json()
    client.post("/api/v1/auth/logout", headers=authenticated_csrf_headers(client))
    register(client, INITIAL)

    assert _patch(client, created["id"], "disable").status_code == 403


def test_me_tells_the_screen_who_is_the_initial_account(client: TestClient) -> None:
    register(client, INITIAL)
    assert client.get("/api/v1/auth/me").json()["is_initial_account"] is True

    client.post("/api/v1/auth/logout", headers=authenticated_csrf_headers(client))
    register(client, OTHER)
    assert client.get("/api/v1/auth/me").json()["is_initial_account"] is False
