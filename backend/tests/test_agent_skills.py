from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import select

from app.agent_catalog.tool_interface import AgenteEmissor, Governanca, SkillToolResult
from app.core.database import SessionLocal
from app.models import User
from app.rag.ingestion import ingest_artifact
from app.rag.providers.mock_embedding_provider import MockEmbeddingProvider
from tests.conftest import csrf_headers

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "app" / "agent_manifest" / "fixtures"
FIXTURE_MANIFEST = (FIXTURES_DIR / "legacy-code-skill.md").read_text(encoding="utf-8")
BUSINESS_RULES_FIXTURE_MANIFEST = (FIXTURES_DIR / "business-rules-skill.md").read_text(encoding="utf-8")
ARCHITECTURE_FIXTURE_MANIFEST = (FIXTURES_DIR / "architecture-skill.md").read_text(encoding="utf-8")

TECHNICIAN = {
    "name": "Tecnica Skills",
    "email": "tecnica.skills@example.com",
    "password": "StrongPassword!123",
}
REGULAR_USER = {
    "name": "Usuaria Comum",
    "email": "usuaria.comum@example.com",
    "password": "StrongPassword!123",
}


def authenticated_csrf_headers(client: TestClient) -> dict[str, str]:
    token = client.cookies.get("agenthub_csrf")
    assert token
    return {"X-CSRF-Token": token}


def register(client: TestClient, user: dict) -> None:
    response = client.post("/api/v1/auth/register", json=user, headers=csrf_headers(client))
    assert response.status_code == 201


def promote(email: str, role: str) -> str:
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        assert user is not None
        user.role = role
        db.commit()
        return user.id


def create_qualified_request(client: TestClient, *, requested_domains: list[str]) -> dict:
    response = client.post(
        "/api/v1/requests",
        json={
            "title": "Avaliar limite de crédito por segmento",
            "problem": "O limite de crédito é global e precisa considerar o segmento do cliente.",
            "objective": "Gerar plano técnico sem executar alterações automaticamente.",
            "context": (
                "O sistema legado calcula o limite de crédito do cliente de forma fixa, "
                "sem considerar o segmento, e isso precisa mudar com segurança."
            ),
            "restrictions": ["Não executar tools"],
            "requested_domains": requested_domains,
        },
        headers=authenticated_csrf_headers(client),
    )
    assert response.status_code == 201
    assert response.json()["status"] == "QUALIFIED"
    return response.json()


def test_import_valid_manifest_registers_and_enables_skill(client: TestClient) -> None:
    register(client, TECHNICIAN)
    promote(TECHNICIAN["email"], "TECHNICIAN")

    response = client.post(
        "/api/v1/agent-skills/import",
        json={"manifest_markdown": FIXTURE_MANIFEST},
        headers=authenticated_csrf_headers(client),
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "approved"
    assert payload["enabled"] is True
    assert payload["domain"] == "codigo_legado"

    catalog_response = client.get("/api/v1/agent-skills")
    assert catalog_response.status_code == 200
    assert any(skill["id"] == payload["id"] for skill in catalog_response.json())


def test_import_invalid_manifest_is_rejected_with_reasons(client: TestClient) -> None:
    register(client, TECHNICIAN)
    promote(TECHNICIAN["email"], "TECHNICIAN")

    incomplete_manifest = "# Agente Incompleto\n\n## Identificação\n- Nome: Incompleto\n"
    response = client.post(
        "/api/v1/agent-skills/import",
        json={"manifest_markdown": incomplete_manifest},
        headers=authenticated_csrf_headers(client),
    )
    assert response.status_code == 422
    message = response.json()["message"]
    # Multiple problems must be reported together (joined by "; "), not just the first one.
    assert message.count(";") >= 1


def test_assisted_creation_registers_skill(client: TestClient) -> None:
    register(client, TECHNICIAN)
    promote(TECHNICIAN["email"], "TECHNICIAN")

    response = client.post(
        "/api/v1/agent-skills",
        json={
            "name": "Agent Skill de Arquitetura",
            "version": "1.0",
            "author_origin": "Equipe AgentHub",
            "domain": "arquitetura_software",
            "objective": "Avaliar impactos arquiteturais de uma mudança.",
            "capabilities": ["Avaliar padrões arquiteturais"],
            "expected_inputs": ["Contexto técnico"],
            "produced_outputs": ["Riscos arquiteturais"],
            "operating_limits": ["Não aprova decisões finais"],
            "input_contract_ref": "solicitacao_analise_schema.v1",
            "output_contract_ref": "resposta_especialista_schema.v1",
            "validation_criteria": ["Contrato válido"],
        },
        headers=authenticated_csrf_headers(client),
    )
    assert response.status_code == 201
    assert response.json()["domain"] == "arquitetura_software"


def test_regular_user_cannot_manage_skills(client: TestClient) -> None:
    register(client, REGULAR_USER)

    response = client.post(
        "/api/v1/agent-skills/import",
        json={"manifest_markdown": FIXTURE_MANIFEST},
        headers=authenticated_csrf_headers(client),
    )
    assert response.status_code == 403


def test_enable_disable_requires_admin(client: TestClient) -> None:
    register(client, TECHNICIAN)
    promote(TECHNICIAN["email"], "TECHNICIAN")

    imported = client.post(
        "/api/v1/agent-skills/import",
        json={"manifest_markdown": FIXTURE_MANIFEST},
        headers=authenticated_csrf_headers(client),
    ).json()

    technician_attempt = client.patch(
        f"/api/v1/agent-skills/{imported['id']}/disable",
        headers=authenticated_csrf_headers(client),
    )
    assert technician_attempt.status_code == 403

    promote(TECHNICIAN["email"], "ADMIN")
    admin_attempt = client.patch(
        f"/api/v1/agent-skills/{imported['id']}/disable",
        headers=authenticated_csrf_headers(client),
    )
    assert admin_attempt.status_code == 200
    assert admin_attempt.json()["enabled"] is False


def test_execute_orchestration_step_runs_skill_and_quality_gate(client: TestClient, monkeypatch) -> None:
    from app.core.config import settings

    with SessionLocal() as db:
        ingest_artifact(
            db,
            artifact_name="CreditLimitService.java",
            content=(
                "O limite de credito hoje eh sempre R$ 5000,00 fixo, sem considerar "
                "o segmento do cliente (varejo, atacado, corporativo)."
            ),
            language="java",
            embedding_provider=MockEmbeddingProvider(),
            max_chars=1000,
            overlap=0,
        )
        db.commit()

    register(client, TECHNICIAN)
    promote(TECHNICIAN["email"], "TECHNICIAN")

    client.post(
        "/api/v1/agent-skills/import",
        json={"manifest_markdown": FIXTURE_MANIFEST},
        headers=authenticated_csrf_headers(client),
    )

    technical_request = create_qualified_request(client, requested_domains=["codigo_legado"])

    monkeypatch.setattr(settings, "llm_enabled", True)
    monkeypatch.setattr(settings, "llm_provider", "mock")

    execution_response = client.post(
        f"/api/v1/agent-skills/requests/{technical_request['id']}/execute",
        headers=authenticated_csrf_headers(client),
    )
    assert execution_response.status_code == 200
    payload = execution_response.json()
    assert payload["invocations_count"] == 1
    assert len(payload["results"]) == 1
    assert payload["results"][0]["agente_emissor"]["dominio"] == "codigo_legado"
    assert payload["verdict"]["reasons"]

    events_response = client.get(f"/api/v1/orchestrations/{technical_request['trace_id']}/events")
    event_types = [event["event_type"] for event in events_response.json()]
    for expected in (
        "AGENT_SKILL_SELECTED",
        "AGENT_SKILL_INVOCATION_STARTED",
        "AGENT_SKILL_INVOCATION_COMPLETED",
        "QUALITY_GATE_EVALUATED",
    ):
        assert expected in event_types

    dashboard_response = client.get("/api/v1/dashboard/summary")
    assert dashboard_response.status_code == 200
    assert dashboard_response.json()["registered_agent_skills"] == 1

    detail_response = client.get(f"/api/v1/requests/{technical_request['id']}")
    assert detail_response.json()["status"] in {"COMPLETED", "VALIDATING"}


def test_execute_orchestration_step_runs_three_skills_in_one_analysis(
    client: TestClient, monkeypatch
) -> None:
    """Proves RFC 5.5's minimum success criterion: at least three Agent Skills
    acting on the same analysis, each with its own invocation, result and
    Quality Gate evaluation — not three separate requests."""
    from app.core.config import settings

    with SessionLocal() as db:
        ingest_artifact(
            db,
            artifact_name="CreditLimitService.java",
            content=(
                "O limite de credito hoje eh sempre R$ 5000,00 fixo, sem considerar "
                "o segmento do cliente (varejo, atacado, corporativo)."
            ),
            language="java",
            embedding_provider=MockEmbeddingProvider(),
            max_chars=1000,
            overlap=0,
        )
        db.commit()

    register(client, TECHNICIAN)
    promote(TECHNICIAN["email"], "TECHNICIAN")

    for manifest in (FIXTURE_MANIFEST, BUSINESS_RULES_FIXTURE_MANIFEST, ARCHITECTURE_FIXTURE_MANIFEST):
        import_response = client.post(
            "/api/v1/agent-skills/import",
            json={"manifest_markdown": manifest},
            headers=authenticated_csrf_headers(client),
        )
        assert import_response.status_code == 201

    technical_request = create_qualified_request(
        client,
        requested_domains=["codigo_legado", "regras_negocio", "arquitetura_software"],
    )

    monkeypatch.setattr(settings, "llm_enabled", True)
    monkeypatch.setattr(settings, "llm_provider", "mock")

    execution_response = client.post(
        f"/api/v1/agent-skills/requests/{technical_request['id']}/execute",
        headers=authenticated_csrf_headers(client),
    )
    assert execution_response.status_code == 200
    payload = execution_response.json()
    assert payload["invocations_count"] == 3
    assert len(payload["results"]) == 3
    assert {result["agente_emissor"]["dominio"] for result in payload["results"]} == {
        "codigo_legado",
        "regras_negocio",
        "arquitetura_software",
    }

    events_response = client.get(f"/api/v1/orchestrations/{technical_request['trace_id']}/events")
    event_types = [event["event_type"] for event in events_response.json()]
    assert event_types.count("AGENT_SKILL_INVOCATION_COMPLETED") == 3
    assert "QUALITY_GATE_EVALUATED" in event_types

    detail_response = client.get(f"/api/v1/requests/{technical_request['id']}")
    assert detail_response.json()["status"] in {"COMPLETED", "VALIDATING"}


def test_execute_over_real_stdio_subprocess(client: TestClient, monkeypatch) -> None:
    """Same flow as test_execute_orchestration_step_runs_skill_and_quality_gate,
    but forces the "stdio" transport: the orchestrator spawns
    `python -m app.agent_catalog.mcp_servers.legacy_code_server` as an actual OS
    subprocess and talks real MCP JSON-RPC to it, instead of the in-memory
    transport the rest of the suite uses for speed. This is the evidence that
    the contract isn't only real "in memory" — it survives a process boundary.
    """
    from app.core.config import settings

    with SessionLocal() as db:
        ingest_artifact(
            db,
            artifact_name="CreditLimitService.java",
            content=(
                "O limite de credito hoje eh sempre R$ 5000,00 fixo, sem considerar "
                "o segmento do cliente (varejo, atacado, corporativo)."
            ),
            language="java",
            embedding_provider=MockEmbeddingProvider(),
            max_chars=1000,
            overlap=0,
        )
        db.commit()

    register(client, TECHNICIAN)
    promote(TECHNICIAN["email"], "TECHNICIAN")

    client.post(
        "/api/v1/agent-skills/import",
        json={"manifest_markdown": FIXTURE_MANIFEST},
        headers=authenticated_csrf_headers(client),
    )

    technical_request = create_qualified_request(client, requested_domains=["codigo_legado"])

    monkeypatch.setattr(settings, "llm_enabled", True)
    monkeypatch.setattr(settings, "llm_provider", "mock")
    monkeypatch.setattr(settings, "mcp_skill_transport", "stdio")

    execution_response = client.post(
        f"/api/v1/agent-skills/requests/{technical_request['id']}/execute",
        headers=authenticated_csrf_headers(client),
    )
    assert execution_response.status_code == 200
    payload = execution_response.json()
    assert payload["invocations_count"] == 1
    assert len(payload["results"]) == 1
    assert payload["results"][0]["agente_emissor"]["dominio"] == "codigo_legado"


def test_execute_without_matching_skill_returns_409(client: TestClient) -> None:
    register(client, TECHNICIAN)
    promote(TECHNICIAN["email"], "TECHNICIAN")

    technical_request = create_qualified_request(client, requested_domains=["regras_negocio"])

    response = client.post(
        f"/api/v1/agent-skills/requests/{technical_request['id']}/execute",
        headers=authenticated_csrf_headers(client),
    )
    assert response.status_code == 409


def test_skill_tool_result_rejects_invalid_confidence_level() -> None:
    with pytest.raises(ValidationError):
        SkillToolResult(
            trace_id="TRC-20260811-AAAAAA",
            agente_emissor=AgenteEmissor(nome="Skill", dominio="codigo_legado"),
            analise_estruturada={
                "resumo_executivo": "resumo",
                "descobertas_tecnicas": [],
                "impactos_mapeados": [],
            },
            governanca=Governanca(
                nivel_confianca="MUITO_ALTO",  # not in the ALTO/MEDIO/BAIXO enum
                justificativa_confianca="teste",
            ),
        )
