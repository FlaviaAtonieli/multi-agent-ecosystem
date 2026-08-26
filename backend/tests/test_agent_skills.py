from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.agent_catalog.tool_interface import AgenteEmissor, Governanca, SkillToolResult
from app.core.database import SessionLocal
from app.rag.ingestion import ingest_artifact
from tests.conftest import (
    authenticated_csrf_headers,
    create_qualified_request,
    enable_real_llm,
    promote,
    real_embedding_provider,
    register,
)

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "app" / "agent_manifest" / "fixtures"
FIXTURE_MANIFEST = (FIXTURES_DIR / "legacy-code-skill.md").read_text(encoding="utf-8")
BUSINESS_RULES_FIXTURE_MANIFEST = (FIXTURES_DIR / "business-rules-skill.md").read_text(encoding="utf-8")
ARCHITECTURE_FIXTURE_MANIFEST = (FIXTURES_DIR / "architecture-skill.md").read_text(encoding="utf-8")
SECURITY_FIXTURE_MANIFEST = (FIXTURES_DIR / "security-skill.md").read_text(encoding="utf-8")

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
    with SessionLocal() as db:
        ingest_artifact(
            db,
            artifact_name="CreditLimitService.java",
            content=(
                "O limite de credito hoje eh sempre R$ 5000,00 fixo, sem considerar "
                "o segmento do cliente (varejo, atacado, corporativo)."
            ),
            language="java",
            embedding_provider=real_embedding_provider(),
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

    enable_real_llm(monkeypatch)

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
    with SessionLocal() as db:
        ingest_artifact(
            db,
            artifact_name="CreditLimitService.java",
            content=(
                "O limite de credito hoje eh sempre R$ 5000,00 fixo, sem considerar "
                "o segmento do cliente (varejo, atacado, corporativo)."
            ),
            language="java",
            embedding_provider=real_embedding_provider(),
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

    enable_real_llm(monkeypatch)

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

    # RFC 5.5 criterio 5: resposta parcial (payload["results"]) e resposta final
    # consolidada precisam ser artefatos distintos, nao o mesmo dado reembalado.
    consolidated = payload["consolidated_response"]
    assert consolidated["trace_id"] == technical_request["trace_id"]
    assert len(consolidated["participating_agents"]) == 3
    assert len(consolidated["invocation_ids"]) == 3
    assert consolidated["quality_gate_approved"] == payload["verdict"]["approved"]
    assert consolidated["requires_human_review"] == payload["verdict"]["requires_human_review"]
    for domain in ("codigo_legado", "regras_negocio", "arquitetura_software"):
        assert f"[{domain}]" in consolidated["technical_synthesis"]

    events_response = client.get(f"/api/v1/orchestrations/{technical_request['trace_id']}/events")
    event_types = [event["event_type"] for event in events_response.json()]
    assert event_types.count("AGENT_SKILL_INVOCATION_COMPLETED") == 3
    assert "QUALITY_GATE_EVALUATED" in event_types
    assert "RESPONSE_CONSOLIDATED" in event_types

    detail_response = client.get(f"/api/v1/requests/{technical_request['id']}")
    detail_payload = detail_response.json()
    assert detail_payload["status"] in {"COMPLETED", "VALIDATING"}
    assert detail_payload["consolidated_response"]["id"] == consolidated["id"]


def test_new_agent_skill_couples_without_orchestrator_changes(
    client: TestClient, monkeypatch
) -> None:
    """RFC 5.5 criterio 7 / RF05: proves a brand-new Agent Skill ("Segurança da
    Informação", added after Código Legado, Regras de Negócio and Arquitetura
    already existed) can be registered and executed through the exact same
    generic codepath as the original three -- import via modelo.md, domain
    selection, MCP invocation, Quality Gate, consolidation -- with zero changes
    to agent_skill_orchestration_service.py, orchestration_service.py or
    quality_gate/service.py (the Orquestrador's core). The only touch points
    for this addition were a domain literal entry and one line in
    mcp_client._DOMAIN_SERVER_MODULES -- see the comments there."""
    with SessionLocal() as db:
        ingest_artifact(
            db,
            artifact_name="CreditLimitService.java",
            content=(
                "O limite de credito hoje eh sempre R$ 5000,00 fixo, sem considerar "
                "o segmento do cliente (varejo, atacado, corporativo)."
            ),
            language="java",
            embedding_provider=real_embedding_provider(),
            max_chars=1000,
            overlap=0,
        )
        db.commit()

    register(client, TECHNICIAN)
    promote(TECHNICIAN["email"], "TECHNICIAN")

    import_response = client.post(
        "/api/v1/agent-skills/import",
        json={"manifest_markdown": SECURITY_FIXTURE_MANIFEST},
        headers=authenticated_csrf_headers(client),
    )
    assert import_response.status_code == 201
    assert import_response.json()["domain"] == "seguranca_informacao"

    technical_request = create_qualified_request(
        client, requested_domains=["seguranca_informacao"]
    )

    enable_real_llm(monkeypatch)

    execution_response = client.post(
        f"/api/v1/agent-skills/requests/{technical_request['id']}/execute",
        headers=authenticated_csrf_headers(client),
    )
    assert execution_response.status_code == 200
    payload = execution_response.json()
    assert payload["invocations_count"] == 1
    assert payload["results"][0]["agente_emissor"]["dominio"] == "seguranca_informacao"
    assert payload["consolidated_response"]["participating_agents"] == [
        payload["results"][0]["agente_emissor"]["nome"]
    ]

    events_response = client.get(f"/api/v1/orchestrations/{technical_request['trace_id']}/events")
    event_types = [event["event_type"] for event in events_response.json()]
    for expected in (
        "AGENT_SKILL_SELECTED",
        "AGENT_SKILL_INVOCATION_COMPLETED",
        "QUALITY_GATE_EVALUATED",
        "RESPONSE_CONSOLIDATED",
    ):
        assert expected in event_types


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
            embedding_provider=real_embedding_provider(),
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

    enable_real_llm(monkeypatch)
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
