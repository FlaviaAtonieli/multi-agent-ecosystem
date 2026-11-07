"""Quando a solicitação pede arquivos, o modelo precisa entregá-los.

Medido em 05/11/2026 com o modelo gratuito dots-3-note e trechos reais da base:
ele ignorou o pedido de arquivos em 2 de 13 tentativas. O Quality Gate avisa
quando faltar. O prompt também reforça a instrução, sem ganho medido (8 de 8
com o prompt antigo e com o novo).
"""

import pytest

from app.agent_catalog.contracts import (
    AgenteEmissor,
    AnaliseEstruturada,
    ArquivoGerado,
    Governanca,
    SkillToolResult,
)
from app.llm.file_request import asks_for_files
from app.llm.prompts import build_technical_planner_prompt
from app.llm.schemas import LLMPlanRequest
from app.quality_gate.service import evaluate


def skill_result(*, confidence: str, files: list[ArquivoGerado] | None = None) -> SkillToolResult:
    return SkillToolResult(
        trace_id="T",
        agente_emissor=AgenteEmissor(nome="Código Legado", dominio="codigo_legado"),
        analise_estruturada=AnaliseEstruturada(resumo_executivo="Índice composto em SEGMENTO e DATA_REF."),
        governanca=Governanca(nivel_confianca=confidence, justificativa_confianca="teste"),
        arquivos=files or [],
    )


PEDE_ARQUIVOS = [
    "Gere um arquivo SQL com o índice composto e um README.md explicando como aplicar.",
    "Quero o script de migração do banco.",
    "Entregar o create_index.sql e o docker-compose.yml",
    "Crie uma classe Java para o novo cálculo de risco.",
    "Escrever os testes unitários do serviço de faturamento.",
    "Me mande os arquivos do projeto",
]

NAO_PEDE = [
    "Mapear o impacto técnico e orientar a correção.",
    "Avaliar como reduzir o tempo do job.",
    "Analisar o código legado e listar riscos.",
    "Explicar a arquitetura sem gerar arquivos.",
    "Não quero script, só a análise.",
]


@pytest.mark.parametrize("text", PEDE_ARQUIVOS)
def test_reconhece_pedido_de_arquivo(text: str) -> None:
    assert asks_for_files(text)


@pytest.mark.parametrize("text", NAO_PEDE)
def test_nao_confunde_analise_com_pedido_de_arquivo(text: str) -> None:
    assert not asks_for_files(text)


def test_ignora_campos_vazios() -> None:
    assert not asks_for_files(None, "", "Avaliar o job.")


def _request(objective: str) -> LLMPlanRequest:
    return LLMPlanRequest(
        technical_request_id="1",
        trace_id="T",
        title="Índice para o RiskBatchJob",
        problem="O arquivo de log mostra full scan.",
        objective=objective,
    )


def test_prompt_reforca_quando_ha_pedido_de_arquivo() -> None:
    prompt = build_technical_planner_prompt(_request("Gere um arquivo SQL com o índice."))

    assert "pede arquivos explicitamente" in prompt
    assert "Não deixe generated_files vazio" in prompt


def test_prompt_normal_quando_nao_ha_pedido() -> None:
    # "arquivo de log" está no problema, não no objetivo: não é um pedido.
    prompt = build_technical_planner_prompt(_request("Avaliar como reduzir o tempo."))

    assert "pede arquivos explicitamente" not in prompt
    assert "lista vazia" in prompt


def test_quality_gate_avisa_quando_arquivos_pedidos_nao_vieram() -> None:
    verdict = evaluate([skill_result(confidence="ALTO")], files_requested=True)

    assert verdict.requires_human_review
    assert any("pediu arquivos" in reason for reason in verdict.reasons)


def test_quality_gate_aceita_quando_os_arquivos_vieram() -> None:
    sql = ArquivoGerado(nome="create_index.sql", conteudo="CREATE INDEX x;")
    result = skill_result(confidence="ALTO", files=[sql])

    verdict = evaluate([result], files_requested=True)

    assert not verdict.requires_human_review
    assert not any("pediu arquivos" in reason for reason in verdict.reasons)


def test_quality_gate_sem_pedido_nao_cobra_arquivos() -> None:
    verdict = evaluate([skill_result(confidence="ALTO")])

    assert not verdict.requires_human_review


# --- pelo caminho real da orquestração ------------------------------------------
# O orquestrador tira o conteúdo dos arquivos da resposta depois de guardá-los
# (skill_artifacts). Conferir result.arquivos ali dava sempre "não vieram".


def _orchestrate(client, monkeypatch, files: list[ArquivoGerado]) -> list[str]:
    from app.services import agent_skill_orchestration_service as service
    from tests.conftest import authenticated_csrf_headers, create_qualified_request, register
    from tests.test_background_orchestration import _start_url, _wait_for_status
    from tests.test_human_review import FIXTURE_MANIFEST

    async def fake(skill, tool_call) -> SkillToolResult:
        return SkillToolResult(
            trace_id=tool_call.trace_id,
            agente_emissor=AgenteEmissor(nome=skill.name, dominio=skill.domain),
            analise_estruturada=AnaliseEstruturada(resumo_executivo="Índice proposto."),
            governanca=Governanca(nivel_confianca="ALTO", justificativa_confianca="ok"),
            arquivos=files,
        )

    monkeypatch.setattr(service, "call_skill_tool", fake)
    register(
        client,
        {"name": "Pede Arquivo", "email": "pede.arquivo@example.com", "password": "StrongPassword!123"},
    )
    headers = authenticated_csrf_headers(client)
    client.post("/api/v1/agent-skills/import", json={"manifest_markdown": FIXTURE_MANIFEST}, headers=headers)
    request = create_qualified_request(client, objective="Gere um arquivo SQL com o índice composto.")
    client.post(_start_url(request["id"]), headers=authenticated_csrf_headers(client))
    _wait_for_status(client, request["id"], "COMPLETED", "VALIDATING", "FAILED")
    events = client.get(f"/api/v1/orchestrations/{request['trace_id']}").json()["events"]
    return next(e for e in events if e["event_type"] == "QUALITY_GATE_EVALUATED")["payload"]["reasons"]


def test_orquestracao_com_os_arquivos_pedidos_nao_acusa_falta(client, monkeypatch) -> None:
    sql = ArquivoGerado(nome="indice.sql", conteudo="CREATE INDEX x;")
    reasons = _orchestrate(client, monkeypatch, [sql])

    assert not any("pediu arquivos" in reason for reason in reasons)


def test_orquestracao_sem_os_arquivos_pedidos_acusa_falta(client, monkeypatch) -> None:
    reasons = _orchestrate(client, monkeypatch, [])

    assert any("pediu arquivos" in reason for reason in reasons)
