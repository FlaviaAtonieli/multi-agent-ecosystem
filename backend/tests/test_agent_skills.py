from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import select

from app.agent_catalog.registry import register_skill
from app.agent_catalog.tool_interface import AgenteEmissor, Governanca, SkillToolResult
from app.agent_manifest.manifest import parse_modelo_md
from app.core.database import SessionLocal
from app.models import AgentSkillInvocation, LLMInvocation, User
from app.rag.ingestion import ingest_artifact
from tests.conftest import (
    REAL_LLM_MODEL,
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
            "author_origin": "Equipe Flav.IA",
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

    skill_results_response = client.get(
        f"/api/v1/orchestrations/{technical_request['trace_id']}/skill-results"
    )
    assert skill_results_response.status_code == 200
    skill_results = skill_results_response.json()
    assert len(skill_results) == 1
    assert skill_results[0]["status"] == "COMPLETED"
    assert skill_results[0]["result"]["agente_emissor"]["dominio"] == "codigo_legado"
    assert skill_results[0]["result"]["analise_estruturada"]["resumo_executivo"]


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


def test_quality_domain_executes_with_real_rag_retrieval(client: TestClient, monkeypatch) -> None:
    """First of 6 new domains (RF da expansao de dominios pos-PAC-VIII):
    "Qualidade e Testes". Registrado via formulario assistido (nao /import),
    ja que persona_instructions -- o que da ao GenericSkillExecutor seu
    enquadramento de dominio -- so e aceito por esse endpoint (ver
    AgentSkillManifestCreate vs. AgentSkillManifestImport). Prova retrieval
    real (ingestao real, sem mock) e nao so o contrato de saida."""
    with SessionLocal() as db:
        ingest_artifact(
            db,
            artifact_name="test-coverage-audit.md",
            content=(
                "Nenhuma suite de teste cobre os tres consumidores de "
                "getLimiteCredito() juntos. OrderFlowIntegrationTest e flaky "
                "em CI por falta de isolamento de dados entre testes."
            ),
            language="markdown",
            embedding_provider=real_embedding_provider(),
            max_chars=1000,
            overlap=0,
        )
        db.commit()

    register(client, TECHNICIAN)
    promote(TECHNICIAN["email"], "TECHNICIAN")

    create_response = client.post(
        "/api/v1/agent-skills",
        json={
            "name": "Agent Skill de Qualidade e Testes",
            "version": "1.0",
            "author_origin": "Equipe Flav.IA",
            "domain": "qualidade_testes",
            "objective": "Avaliar cobertura de testes e risco de regressao de uma mudanca solicitada.",
            "capabilities": [
                "Recuperar evidencia de cobertura de teste e testes existentes",
                "Identificar lacunas de cobertura em componentes criticos",
                "Sinalizar testes instaveis (flaky) e risco de regressao sem rede de seguranca",
            ],
            "expected_inputs": ["Problema tecnico", "Objetivo", "Contexto da solicitacao"],
            "produced_outputs": [
                "Resumo executivo", "Lacunas de cobertura identificadas", "Nivel de confianca",
            ],
            "operating_limits": ["Nao escreve nem executa testes automaticamente"],
            "input_contract_ref": "solicitacao_analise_schema.v1",
            "output_contract_ref": "resposta_especialista_schema.v1",
            "validation_criteria": ["Contrato de saida valido"],
            "persona_instructions": (
                "Voce e um especialista em qualidade de software e estrategia de testes "
                "automatizados. Analise a solicitacao focando em: cobertura de teste existente "
                "nos componentes envolvidos, lacunas em cenarios criticos, testes instaveis "
                "(flaky) e risco de regressao quando nao ha teste automatizado cobrindo a "
                "mudanca. Baseie-se nas evidencias recuperadas da base de conhecimento."
            ),
        },
        headers=authenticated_csrf_headers(client),
    )
    assert create_response.status_code == 201
    assert create_response.json()["domain"] == "qualidade_testes"

    technical_request = create_qualified_request(client, requested_domains=["qualidade_testes"])

    enable_real_llm(monkeypatch)

    execution_response = client.post(
        f"/api/v1/agent-skills/requests/{technical_request['id']}/execute",
        headers=authenticated_csrf_headers(client),
    )
    assert execution_response.status_code == 200
    payload = execution_response.json()
    assert payload["invocations_count"] == 1
    result = payload["results"][0]
    assert result["agente_emissor"]["dominio"] == "qualidade_testes"
    # Retrieval precisa ter de fato encontrado o chunk ingerido acima -- prova
    # que o pipeline RAG (ingestao + embeddings + retrieval) roda de verdade
    # pro dominio novo, nao so que o contrato de saida bate.
    assert len(result["analise_estruturada"]["descobertas_tecnicas"]) > 0


def test_observability_domain_executes_with_real_rag_retrieval(client: TestClient, monkeypatch) -> None:
    """Segundo dos 6 dominios novos: "Observabilidade e Monitoramento". Mesmo
    padrao do teste de Qualidade e Testes acima -- formulario assistido (pra
    persona_instructions), ingestao e retrieval reais, execucao real."""
    with SessionLocal() as db:
        ingest_artifact(
            db,
            artifact_name="incident-postmortem-riskbatchjob.md",
            content=(
                "RiskBatchJob falhou silenciosamente por 6 dias sem nenhum alerta. "
                "Nenhum dos componentes do modulo de limite de credito emite metrica "
                "de execucao, log estruturado ou alerta de job ausente."
            ),
            language="markdown",
            embedding_provider=real_embedding_provider(),
            max_chars=1000,
            overlap=0,
        )
        db.commit()

    register(client, TECHNICIAN)
    promote(TECHNICIAN["email"], "TECHNICIAN")

    create_response = client.post(
        "/api/v1/agent-skills",
        json={
            "name": "Agent Skill de Observabilidade e Monitoramento",
            "version": "1.0",
            "author_origin": "Equipe Flav.IA",
            "domain": "observabilidade_monitoramento",
            "objective": (
                "Avaliar instrumentacao (logs, metricas, alertas) afetada por uma mudanca "
                "solicitada."
            ),
            "capabilities": [
                "Recuperar evidencia de incidentes e lacunas de observabilidade ja registrados",
                "Identificar componentes sem log estruturado, metrica ou alerta",
                "Sinalizar risco de falha silenciosa numa mudanca proposta",
            ],
            "expected_inputs": ["Problema tecnico", "Objetivo", "Contexto da solicitacao"],
            "produced_outputs": [
                "Resumo executivo", "Lacunas de observabilidade identificadas", "Nivel de confianca",
            ],
            "operating_limits": ["Nao configura alertas nem dashboards automaticamente"],
            "input_contract_ref": "solicitacao_analise_schema.v1",
            "output_contract_ref": "resposta_especialista_schema.v1",
            "validation_criteria": ["Contrato de saida valido"],
            "persona_instructions": (
                "Voce e um especialista em observabilidade e monitoramento de sistemas. "
                "Analise a solicitacao focando em: se os componentes envolvidos emitem log "
                "estruturado, metrica e alerta adequados, historico de incidentes causados "
                "por falta de visibilidade (falha silenciosa), e o risco de uma mudanca "
                "introduzir um problema que nao seria detectado proativamente. Baseie-se "
                "nas evidencias recuperadas da base de conhecimento."
            ),
        },
        headers=authenticated_csrf_headers(client),
    )
    assert create_response.status_code == 201
    assert create_response.json()["domain"] == "observabilidade_monitoramento"

    technical_request = create_qualified_request(
        client, requested_domains=["observabilidade_monitoramento"]
    )

    enable_real_llm(monkeypatch)

    execution_response = client.post(
        f"/api/v1/agent-skills/requests/{technical_request['id']}/execute",
        headers=authenticated_csrf_headers(client),
    )
    assert execution_response.status_code == 200
    payload = execution_response.json()
    assert payload["invocations_count"] == 1
    result = payload["results"][0]
    assert result["agente_emissor"]["dominio"] == "observabilidade_monitoramento"
    assert len(result["analise_estruturada"]["descobertas_tecnicas"]) > 0


def test_performance_domain_executes_with_real_rag_retrieval(client: TestClient, monkeypatch) -> None:
    """Terceiro dos 6 dominios novos: "Performance e Escalabilidade". Mesmo
    padrao dos dois anteriores."""
    with SessionLocal() as db:
        ingest_artifact(
            db,
            artifact_name="riskbatchjob-performance-profile.md",
            content=(
                "RiskBatchJob itera sequencialmente sobre todos os clientes, um N+1 "
                "classico: uma consulta separada ao banco por cliente, sem batching, "
                "sem indice em CUSTOMER_ORDER.CUSTOMER_ID, crescendo linearmente com a "
                "base de clientes."
            ),
            language="markdown",
            embedding_provider=real_embedding_provider(),
            max_chars=1000,
            overlap=0,
        )
        db.commit()

    register(client, TECHNICIAN)
    promote(TECHNICIAN["email"], "TECHNICIAN")

    create_response = client.post(
        "/api/v1/agent-skills",
        json={
            "name": "Agent Skill de Performance e Escalabilidade",
            "version": "1.0",
            "author_origin": "Equipe Flav.IA",
            "domain": "performance_escalabilidade",
            "objective": (
                "Avaliar gargalos de performance e risco de escalabilidade afetados "
                "por uma mudanca solicitada."
            ),
            "capabilities": [
                "Recuperar evidencia de gargalos de performance ja registrados",
                "Identificar ausencia de indice, cache ou batching em componentes criticos",
                "Sinalizar risco de escalabilidade quando o crescimento de carga e linear",
            ],
            "expected_inputs": ["Problema tecnico", "Objetivo", "Contexto da solicitacao"],
            "produced_outputs": [
                "Resumo executivo", "Gargalos de performance identificados", "Nivel de confianca",
            ],
            "operating_limits": ["Nao altera indices, cache ou infraestrutura automaticamente"],
            "input_contract_ref": "solicitacao_analise_schema.v1",
            "output_contract_ref": "resposta_especialista_schema.v1",
            "validation_criteria": ["Contrato de saida valido"],
            "persona_instructions": (
                "Voce e um especialista em performance e escalabilidade de sistemas. "
                "Analise a solicitacao focando em: padroes de consulta ineficientes "
                "(ex.: N+1), ausencia de indice/cache/batching, risco de o componente "
                "nao escalar com o crescimento de carga, e historico de gargalos ja "
                "registrados. Baseie-se nas evidencias recuperadas da base de conhecimento."
            ),
        },
        headers=authenticated_csrf_headers(client),
    )
    assert create_response.status_code == 201
    assert create_response.json()["domain"] == "performance_escalabilidade"

    technical_request = create_qualified_request(
        client, requested_domains=["performance_escalabilidade"]
    )

    enable_real_llm(monkeypatch)

    execution_response = client.post(
        f"/api/v1/agent-skills/requests/{technical_request['id']}/execute",
        headers=authenticated_csrf_headers(client),
    )
    assert execution_response.status_code == 200
    payload = execution_response.json()
    assert payload["invocations_count"] == 1
    result = payload["results"][0]
    assert result["agente_emissor"]["dominio"] == "performance_escalabilidade"
    assert len(result["analise_estruturada"]["descobertas_tecnicas"]) > 0


def test_data_privacy_domain_executes_with_real_rag_retrieval(client: TestClient, monkeypatch) -> None:
    """Quarto dos 6 dominios novos: "Dados e Privacidade (LGPD)". Mesmo
    padrao dos tres anteriores."""
    with SessionLocal() as db:
        ingest_artifact(
            db,
            artifact_name="lgpd-gap-audit.md",
            content=(
                "CUSTOMER guarda NOME e EMAIL em texto plano, sem base legal "
                "documentada, sem politica de retencao, sem fluxo de direito do "
                "titular para acesso, correcao ou eliminacao de dados pessoais."
            ),
            language="markdown",
            embedding_provider=real_embedding_provider(),
            max_chars=1000,
            overlap=0,
        )
        db.commit()

    register(client, TECHNICIAN)
    promote(TECHNICIAN["email"], "TECHNICIAN")

    create_response = client.post(
        "/api/v1/agent-skills",
        json={
            "name": "Agent Skill de Dados e Privacidade (LGPD)",
            "version": "1.0",
            "author_origin": "Equipe Flav.IA",
            "domain": "dados_privacidade",
            "objective": (
                "Avaliar lacunas de conformidade com a LGPD afetadas por uma mudanca "
                "solicitada."
            ),
            "capabilities": [
                "Recuperar evidencia de lacunas de conformidade ja registradas",
                "Identificar ausencia de base legal, retencao ou minimizacao de dados",
                "Sinalizar exposicao de dado pessoal alem do necessario",
            ],
            "expected_inputs": ["Problema tecnico", "Objetivo", "Contexto da solicitacao"],
            "produced_outputs": [
                "Resumo executivo", "Lacunas de conformidade identificadas", "Nivel de confianca",
            ],
            "operating_limits": ["Nao aprova conformidade legal final"],
            "input_contract_ref": "solicitacao_analise_schema.v1",
            "output_contract_ref": "resposta_especialista_schema.v1",
            "validation_criteria": ["Contrato de saida valido"],
            "persona_instructions": (
                "Voce e um especialista em protecao de dados e conformidade com a "
                "LGPD. Analise a solicitacao focando em: quais dados pessoais estao "
                "envolvidos, se ha base legal e politica de retencao documentadas, se "
                "ha minimizacao de dados, e risco de exposicao alem do necessario. "
                "Baseie-se nas evidencias recuperadas da base de conhecimento."
            ),
        },
        headers=authenticated_csrf_headers(client),
    )
    assert create_response.status_code == 201
    assert create_response.json()["domain"] == "dados_privacidade"

    technical_request = create_qualified_request(client, requested_domains=["dados_privacidade"])

    enable_real_llm(monkeypatch)

    execution_response = client.post(
        f"/api/v1/agent-skills/requests/{technical_request['id']}/execute",
        headers=authenticated_csrf_headers(client),
    )
    assert execution_response.status_code == 200
    payload = execution_response.json()
    assert payload["invocations_count"] == 1
    result = payload["results"][0]
    assert result["agente_emissor"]["dominio"] == "dados_privacidade"
    assert len(result["analise_estruturada"]["descobertas_tecnicas"]) > 0


def test_infrastructure_domain_executes_with_real_rag_retrieval(client: TestClient, monkeypatch) -> None:
    """Quinto dos 6 dominios novos: "Infraestrutura e DevOps". Mesmo padrao
    dos quatro anteriores."""
    with SessionLocal() as db:
        ingest_artifact(
            db,
            artifact_name="deployment-process-notes.md",
            content=(
                "Nao existe pipeline de CI/CD, infraestrutura como codigo ou rollback "
                "automatizado. Deploy e manual via scp e SSH. Credencial de banco fica "
                "num arquivo .properties copiado manualmente a cada deploy."
            ),
            language="markdown",
            embedding_provider=real_embedding_provider(),
            max_chars=1000,
            overlap=0,
        )
        db.commit()

    register(client, TECHNICIAN)
    promote(TECHNICIAN["email"], "TECHNICIAN")

    create_response = client.post(
        "/api/v1/agent-skills",
        json={
            "name": "Agent Skill de Infraestrutura e DevOps",
            "version": "1.0",
            "author_origin": "Equipe Flav.IA",
            "domain": "infraestrutura_devops",
            "objective": (
                "Avaliar processo de deploy, IaC e paridade de ambientes afetados por "
                "uma mudanca solicitada."
            ),
            "capabilities": [
                "Recuperar evidencia de lacunas de processo de deploy ja registradas",
                "Identificar ausencia de automacao de build/deploy/rollback",
                "Sinalizar risco de falta de paridade entre ambientes",
            ],
            "expected_inputs": ["Problema tecnico", "Objetivo", "Contexto da solicitacao"],
            "produced_outputs": [
                "Resumo executivo", "Lacunas de infraestrutura identificadas", "Nivel de confianca",
            ],
            "operating_limits": ["Nao executa deploy nem altera infraestrutura automaticamente"],
            "input_contract_ref": "solicitacao_analise_schema.v1",
            "output_contract_ref": "resposta_especialista_schema.v1",
            "validation_criteria": ["Contrato de saida valido"],
            "persona_instructions": (
                "Voce e um especialista em infraestrutura e DevOps. Analise a "
                "solicitacao focando em: processo de build/deploy automatizado, "
                "infraestrutura como codigo, plano de rollback, e paridade entre "
                "ambiente de teste e producao. Baseie-se nas evidencias recuperadas "
                "da base de conhecimento."
            ),
        },
        headers=authenticated_csrf_headers(client),
    )
    assert create_response.status_code == 201
    assert create_response.json()["domain"] == "infraestrutura_devops"

    technical_request = create_qualified_request(
        client, requested_domains=["infraestrutura_devops"]
    )

    enable_real_llm(monkeypatch)

    execution_response = client.post(
        f"/api/v1/agent-skills/requests/{technical_request['id']}/execute",
        headers=authenticated_csrf_headers(client),
    )
    assert execution_response.status_code == 200
    payload = execution_response.json()
    assert payload["invocations_count"] == 1
    result = payload["results"][0]
    assert result["agente_emissor"]["dominio"] == "infraestrutura_devops"
    assert len(result["analise_estruturada"]["descobertas_tecnicas"]) > 0


def test_api_integration_domain_executes_with_real_rag_retrieval(client: TestClient, monkeypatch) -> None:
    """Sexto e ultimo dos 6 dominios novos: "APIs e Integrações". Mesmo
    padrao dos cinco anteriores."""
    with SessionLocal() as db:
        ingest_artifact(
            db,
            artifact_name="breaking-change-incident.md",
            content=(
                "O servico externo de score mudou o formato da resposta sem aviso "
                "previo, sem versionamento de URL, sem teste de contrato. O erro de "
                "parsing foi tratado silenciosamente, escondendo a quebra de integracao "
                "por 3 dias."
            ),
            language="markdown",
            embedding_provider=real_embedding_provider(),
            max_chars=1000,
            overlap=0,
        )
        db.commit()

    register(client, TECHNICIAN)
    promote(TECHNICIAN["email"], "TECHNICIAN")

    create_response = client.post(
        "/api/v1/agent-skills",
        json={
            "name": "Agent Skill de APIs e Integrações",
            "version": "1.0",
            "author_origin": "Equipe Flav.IA",
            "domain": "apis_integracoes",
            "objective": (
                "Avaliar contratos de API e risco de integracao afetados por uma "
                "mudanca solicitada."
            ),
            "capabilities": [
                "Recuperar evidencia de incidentes de integracao ja registrados",
                "Identificar ausencia de versionamento, timeout ou circuit breaker",
                "Sinalizar risco de quebra silenciosa de contrato de API",
            ],
            "expected_inputs": ["Problema tecnico", "Objetivo", "Contexto da solicitacao"],
            "produced_outputs": [
                "Resumo executivo", "Lacunas de contrato/integracao identificadas", "Nivel de confianca",
            ],
            "operating_limits": ["Nao altera contratos de API nem integracoes automaticamente"],
            "input_contract_ref": "solicitacao_analise_schema.v1",
            "output_contract_ref": "resposta_especialista_schema.v1",
            "validation_criteria": ["Contrato de saida valido"],
            "persona_instructions": (
                "Voce e um especialista em APIs e integracoes. Analise a solicitacao "
                "focando em: versionamento, timeout e circuit breaker em chamadas a "
                "servicos internos ou externos, teste de contrato, e historico de "
                "incidentes de mudanca nao anunciada. Baseie-se nas evidencias "
                "recuperadas da base de conhecimento."
            ),
        },
        headers=authenticated_csrf_headers(client),
    )
    assert create_response.status_code == 201
    assert create_response.json()["domain"] == "apis_integracoes"

    technical_request = create_qualified_request(client, requested_domains=["apis_integracoes"])

    enable_real_llm(monkeypatch)

    execution_response = client.post(
        f"/api/v1/agent-skills/requests/{technical_request['id']}/execute",
        headers=authenticated_csrf_headers(client),
    )
    assert execution_response.status_code == 200
    payload = execution_response.json()
    assert payload["invocations_count"] == 1
    result = payload["results"][0]
    assert result["agente_emissor"]["dominio"] == "apis_integracoes"
    assert len(result["analise_estruturada"]["descobertas_tecnicas"]) > 0


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


def test_execute_rejects_model_not_in_allowlist(client: TestClient) -> None:
    register(client, TECHNICIAN)
    promote(TECHNICIAN["email"], "TECHNICIAN")

    client.post(
        "/api/v1/agent-skills/import",
        json={"manifest_markdown": FIXTURE_MANIFEST},
        headers=authenticated_csrf_headers(client),
    )
    technical_request = create_qualified_request(client, requested_domains=["codigo_legado"])

    response = client.post(
        f"/api/v1/agent-skills/requests/{technical_request['id']}/execute",
        json={"model": "not-a-real-model"},
        headers=authenticated_csrf_headers(client),
    )
    assert response.status_code == 422


def test_execute_uses_requested_model_override(client: TestClient, monkeypatch) -> None:
    """Proves the per-execution model choice actually reaches the provider call,
    not just accepted-and-ignored: picks a model other than LLM_MODEL and checks
    the persisted LLMInvocation used it."""
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

    from app.core.config import settings

    enable_real_llm(monkeypatch)
    override_model = "z-ai/glm-5.2:free"
    assert override_model != REAL_LLM_MODEL
    monkeypatch.setattr(settings, "llm_allowed_models", f"{REAL_LLM_MODEL},{override_model}")

    execution_response = client.post(
        f"/api/v1/agent-skills/requests/{technical_request['id']}/execute",
        json={"model": override_model},
        headers=authenticated_csrf_headers(client),
    )
    assert execution_response.status_code == 200

    with SessionLocal() as db:
        invocation = db.scalar(
            select(LLMInvocation).where(LLMInvocation.technical_request_id == technical_request["id"])
        )
        assert invocation is not None
        assert invocation.model == override_model


def test_execute_without_matching_skill_returns_409(client: TestClient) -> None:
    register(client, TECHNICIAN)
    promote(TECHNICIAN["email"], "TECHNICIAN")

    technical_request = create_qualified_request(client, requested_domains=["regras_negocio"])

    response = client.post(
        f"/api/v1/agent-skills/requests/{technical_request['id']}/execute",
        headers=authenticated_csrf_headers(client),
    )
    assert response.status_code == 409


def test_skill_usage_ranking_counts_only_official_and_completed(client: TestClient) -> None:
    register(client, TECHNICIAN)
    promote(TECHNICIAN["email"], "TECHNICIAN")

    legacy_skill = client.post(
        "/api/v1/agent-skills/import",
        json={"manifest_markdown": FIXTURE_MANIFEST},
        headers=authenticated_csrf_headers(client),
    ).json()
    business_skill = client.post(
        "/api/v1/agent-skills/import",
        json={"manifest_markdown": BUSINESS_RULES_FIXTURE_MANIFEST},
        headers=authenticated_csrf_headers(client),
    ).json()

    technical_request = create_qualified_request(client)

    with SessionLocal() as db:
        technician = db.query(User).filter(User.email == TECHNICIAN["email"]).one()
        private_skill = register_skill(
            db,
            manifest=parse_modelo_md(ARCHITECTURE_FIXTURE_MANIFEST),
            submitted_by=technician,
            owner_id=technician.id,
            visibility="PRIVATE",
        )
        db.commit()

        def _insert(skill_id: str, status: str, count: int) -> None:
            for index in range(count):
                db.add(
                    AgentSkillInvocation(
                        technical_request_id=technical_request["id"],
                        agent_skill_id=skill_id,
                        trace_id=technical_request["trace_id"],
                        invocation_id=f"{skill_id}-{status}-{index}",
                        input_hash=f"hash-{skill_id}-{status}-{index}",
                        status=status,
                    )
                )

        # legacy: 3 COMPLETED + 1 FAILED (FAILED must not count).
        _insert(legacy_skill["id"], "COMPLETED", 3)
        _insert(legacy_skill["id"], "FAILED", 1)
        # business rules: fewer COMPLETED than legacy, so it ranks second.
        _insert(business_skill["id"], "COMPLETED", 1)
        # private skill: most invocations of all, but must never appear (not OFFICIAL).
        _insert(private_skill.id, "COMPLETED", 5)
        db.commit()

    response = client.get("/api/v1/agent-skills/ranking", headers=authenticated_csrf_headers(client))
    assert response.status_code == 200
    ranking = response.json()

    ranked_ids = [entry["id"] for entry in ranking]
    assert private_skill.id not in ranked_ids
    assert ranked_ids[0] == legacy_skill["id"]
    assert ranking[0]["usage_count"] == 3
    assert ranked_ids[1] == business_skill["id"]
    assert ranking[1]["usage_count"] == 1


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
