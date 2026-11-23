"""Relator do comitê: a skill que declara um parecer final roda por último e recebe os
pareceres das outras.

Pedido de 23/11/2026: no comitê jurídico a orquestração equivale a um julgamento, e
no de saúde ela fecha uma avaliação do paciente. Sem relator, as skills rodam juntas e
nenhuma vê o que as outras disseram.
"""

import asyncio

from fastapi.testclient import TestClient

from app.agent_catalog.contracts import (
    AchadoTecnico,
    AgenteEmissor,
    AnaliseEstruturada,
    ArquivoGerado,
    Governanca,
    SkillToolResult,
)
from app.core.config import settings
from app.llm.prompts import build_technical_planner_prompt
from app.llm.schemas import LLMPlanRequest
from app.quality_gate.service import evaluate, relator_coverage
from app.services import agent_skill_orchestration_service as service
from app.services.relator import PLATFORM_RELATOR_NAME
from app.services.team_context import build_relator_context, is_relator
from tests.conftest import register
from tests.test_team_context import _create_skill, _run

USER = {"name": "Comitê Jurídico", "email": "comite.juridico@example.com", "password": "StrongPassword!123"}


def _result(
    name: str, summary: str, risks: list[str] | None = None, sources: list[str] | None = None
) -> SkillToolResult:
    return SkillToolResult(
        trace_id="T",
        agente_emissor=AgenteEmissor(nome=name, dominio=f"direito_{name.lower()}"),
        analise_estruturada=AnaliseEstruturada(
            resumo_executivo=summary,
            impactos_mapeados=risks or [],
            descobertas_tecnicas=[
                AchadoTecnico(item_identificado=source, descricao_detalhada="Trecho recuperado.")
                for source in sources or []
            ],
        ),
        governanca=Governanca(nivel_confianca="ALTO", justificativa_confianca="ok"),
    )


# --- quem é relator -----------------------------------------------------------


def test_skill_que_entrega_parecer_ou_avaliacao_final_e_relatora() -> None:
    assert is_relator({"produced_outputs": ["Parecer final do comitê"]})
    assert is_relator({"produced_outputs": ["Pontos fortes", "Avaliação final do paciente"]})
    assert is_relator({"produced_outputs": ["AVALIACAO FINAL"]})


def test_parecer_de_uma_area_so_nao_e_relator() -> None:
    assert not is_relator({"produced_outputs": ["Parecer jurídico", "Leis aplicáveis"]})
    assert not is_relator({"produced_outputs": ["index.html"]})
    assert not is_relator({})


# --- o que o relator recebe ----------------------------------------------------


def test_contexto_do_relator_leva_resumo_e_riscos_de_cada_agente() -> None:
    context = build_relator_context(
        [
            _result("Advogado", "A ação tem base.", ["O contrato foi assinado."], sources=["credito.md"]),
            _result("Mestre de Leis", "Aplica-se o CDC."),
        ]
    )

    assert "[Advogado] A ação tem base." in context
    assert "- O contrato foi assinado." in context
    assert "[Mestre de Leis] Aplica-se o CDC." in context
    # O nome de um trecho recuperado não é um ponto do agente.
    assert "credito.md" not in context


def test_contexto_do_relator_tem_limite_e_divide_o_espaco() -> None:
    longo = [f"Ponto {numero} " + "x" * 200 for numero in range(100)]
    context = build_relator_context(
        [_result("Advogado", "Resumo.", longo), _result("Contratos", "Resumo curto.")], max_chars=2000
    )

    assert len(context) <= 2000
    assert "[Contratos] Resumo curto." in context


def test_prompt_do_relator_pede_parecer_final_a_partir_dos_pareceres() -> None:
    prompt = build_technical_planner_prompt(
        LLMPlanRequest(
            technical_request_id="1",
            trace_id="T",
            title="Processo",
            problem="Ação de cobrança.",
            objective="Avaliar o processo.",
            team_context="[Advogado] A ação tem base.",
            relator=True,
        )
    )

    assert "relator" in prompt
    assert "[Advogado] A ação tem base." in prompt
    assert "Entregas dos outros agentes" not in prompt


# --- a orquestração com relator ----------------------------------------------


def _spy(monkeypatch) -> list:
    calls: list = []

    async def fake(skill, tool_call) -> SkillToolResult:
        calls.append((skill.name, tool_call.team_context, tool_call.relator))
        await asyncio.sleep(0.05)
        files = []
        if skill.name == "Programação":
            files = [ArquivoGerado(nome="index.html", conteudo="<p>jogo</p>")]
        return SkillToolResult(
            trace_id=tool_call.trace_id,
            agente_emissor=AgenteEmissor(nome=skill.name, dominio=skill.domain),
            analise_estruturada=AnaliseEstruturada(resumo_executivo=f"Resumo de {skill.name}."),
            governanca=Governanca(nivel_confianca="ALTO", justificativa_confianca="ok"),
            arquivos=files,
        )

    monkeypatch.setattr(service, "call_skill_tool", fake)
    return calls


def test_relator_roda_depois_e_recebe_os_pareceres(client: TestClient, monkeypatch) -> None:
    register(client, USER)
    _create_skill(client, "Advogado", "Direito", ["Parecer jurídico"])
    _create_skill(client, "Contratos", "Direito", ["Análise do contrato"])
    _create_skill(client, "Relator", "Relatoria", ["Parecer final do comitê"])
    calls = _spy(monkeypatch)

    request = _run(client, "Avaliar os pontos fortes e fracos do processo.")

    assert sorted(name for name, _, _ in calls[:2]) == ["Advogado", "Contratos"]
    assert all(context is None and not relator for _, context, relator in calls[:2])
    name, context, relator = calls[2]
    assert name == "Relator"
    assert relator is True
    assert "Resumo de Advogado." in context
    assert "Resumo de Contratos." in context
    events = client.get(f"/api/v1/orchestrations/{request['trace_id']}").json()["events"]
    shared = [event for event in events if event["event_type"] == "RELATOR_CONTEXT_SHARED"]
    assert len(shared) == 1
    assert shared[0]["payload"]["relators"] == ["Relator"]


def test_relator_sozinho_roda_como_qualquer_skill(client: TestClient, monkeypatch) -> None:
    register(client, USER)
    _create_skill(client, "Relator", "Relatoria", ["Parecer final do comitê"])
    calls = _spy(monkeypatch)

    _run(client, "Avaliar os pontos fortes e fracos do processo.")

    assert calls == [("Relator", None, False)]


def test_com_codigo_o_relator_fecha_depois_do_implementador(client: TestClient, monkeypatch) -> None:
    register(client, USER)
    _create_skill(client, "UX", "ux_jogos", ["ACESSIBILIDADE.md"])
    _create_skill(client, "Programação", "programacao_jogos", ["index.html", "game.js"])
    _create_skill(client, "Relator", "Relatoria", ["Avaliação final da entrega"])
    calls = _spy(monkeypatch)

    _run(client, "Gere o código-fonte do jogo em index.html e game.js.")

    assert [name for name, _, _ in calls] == ["UX", "Programação", "Relator"]
    assert "Resumo de Programação." in calls[2][1]
    assert "Resumo de UX." in calls[2][1]


def test_sem_relator_no_comite_entra_o_relator_da_plataforma(client: TestClient, monkeypatch) -> None:
    register(client, USER)
    _create_skill(client, "Advogado", "Direito", ["Parecer jurídico"])
    _create_skill(client, "Contratos", "Direito", ["Análise do contrato"])
    calls = _spy(monkeypatch)

    request = _run(client, "Avaliar os pontos fortes e fracos do processo.")

    assert sorted(name for name, _, _ in calls[:2]) == ["Advogado", "Contratos"]
    name, context, relator = calls[2]
    assert name == PLATFORM_RELATOR_NAME
    assert relator is True
    assert "Resumo de Advogado." in context
    events = client.get(f"/api/v1/orchestrations/{request['trace_id']}").json()["events"]
    gate = [e for e in events if e["event_type"] == "QUALITY_GATE_EVALUATED"][-1]
    assert set(gate["payload"]["relator_coverage"]) == {"Advogado", "Contratos"}


def test_relator_da_plataforma_e_criado_uma_vez_e_ninguem_edita(client: TestClient, monkeypatch) -> None:
    register(client, USER)
    _create_skill(client, "Advogado", "Direito", ["Parecer jurídico"])
    _create_skill(client, "Contratos", "Direito", ["Análise do contrato"])
    _spy(monkeypatch)

    _run(client, "Avaliar os pontos fortes e fracos do processo.")
    _run(client, "Avaliar de novo os pontos fortes e fracos do processo.")

    skills = client.get("/api/v1/agent-skills?only_active=false").json()
    relatores = [s for s in skills if s["name"] == PLATFORM_RELATOR_NAME]
    assert len(relatores) == 1
    assert relatores[0]["owner_id"] is None
    assert relatores[0]["visibility"] == "OFFICIAL"


def test_com_um_agente_so_nao_ha_relator(client: TestClient, monkeypatch) -> None:
    register(client, USER)
    _create_skill(client, "Advogado", "Direito", ["Parecer jurídico"])
    calls = _spy(monkeypatch)

    _run(client, "Avaliar os pontos fortes e fracos do processo.")

    assert calls == [("Advogado", None, False)]


def test_relator_da_plataforma_pode_ser_desligado(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(settings, "orchestration_platform_relator", False)
    register(client, USER)
    _create_skill(client, "Advogado", "Direito", ["Parecer jurídico"])
    _create_skill(client, "Contratos", "Direito", ["Análise do contrato"])
    calls = _spy(monkeypatch)

    _run(client, "Avaliar os pontos fortes e fracos do processo.")

    assert all(context is None and not relator for _, context, relator in calls)
    assert len(calls) == 2


# --- cobertura do parecer final (Quality Gate) ---------------------------------


def test_cobertura_mede_quanto_de_cada_parecer_o_relator_considerou() -> None:
    advogado = _result("Advogado", "Contrato assinado prova a dívida.", ["Prescrição"])
    contratos = _result("Contratos", "Cláusula penal abusiva reduz multa.")
    relator = _result(
        "Relator", "O contrato assinado prova a dívida e a prescrição não ocorreu. Conclusão favorável."
    )

    coverage = relator_coverage(relator, [advogado, contratos])

    assert coverage["Advogado"] >= 0.6
    assert coverage["Contratos"] == 0.0


def test_quality_gate_pede_revisao_quando_o_relator_ignora_um_agente() -> None:
    advogado = _result("Advogado", "Contrato assinado prova a dívida.")
    contratos = _result("Contratos", "Cláusula penal abusiva reduz multa.")
    relator = _result("Relator", "O contrato assinado prova a dívida.")

    verdict = evaluate([advogado, contratos, relator], relator_names={"Relator"})

    assert verdict.requires_human_review
    assert any("não considera" in reason and "Contratos" in reason for reason in verdict.reasons)
    assert verdict.relator_coverage is not None
    assert verdict.relator_coverage["Contratos"] == 0.0


def test_quality_gate_aprova_quando_o_relator_considera_todos() -> None:
    advogado = _result("Advogado", "Contrato assinado prova a dívida.")
    contratos = _result("Contratos", "Cláusula penal abusiva reduz multa.")
    relator = _result(
        "Relator", "Contrato assinado prova a dívida; a cláusula penal abusiva reduz a multa."
    )

    verdict = evaluate([advogado, contratos, relator], relator_names={"Relator"})

    assert verdict.approved
    assert not verdict.requires_human_review
    assert any("considera todos os agentes" in reason for reason in verdict.reasons)


def test_fontes_iguais_nao_inflam_a_cobertura() -> None:
    # Todos os agentes citam os mesmos anexos; isso não mostra que o relator leu o agente.
    contratos = _result("Contratos", "Cláusula penal abusiva reduz multa.", sources=["contrato_academia.txt"])
    relator = _result("Relator", "Conclusão favorável.", sources=["contrato_academia.txt"])

    assert relator_coverage(relator, [contratos])["Contratos"] == 0.0


def test_sem_relator_o_quality_gate_nao_mede_cobertura() -> None:
    verdict = evaluate([_result("Advogado", "Contrato assinado prova a dívida.")])

    assert verdict.relator_coverage is None


def test_orquestracao_com_relator_mede_a_cobertura(client: TestClient, monkeypatch) -> None:
    register(client, USER)
    _create_skill(client, "Advogado", "Direito", ["Parecer jurídico"])
    _create_skill(client, "Relator", "Relatoria", ["Parecer final do comitê"])
    _spy(monkeypatch)

    request = _run(client, "Avaliar os pontos fortes e fracos do processo.")

    events = client.get(f"/api/v1/orchestrations/{request['trace_id']}").json()["events"]
    gate = [event for event in events if event["event_type"] == "QUALITY_GATE_EVALUATED"][-1]
    assert "Advogado" in gate["payload"]["relator_coverage"]
