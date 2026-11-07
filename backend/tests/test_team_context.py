"""Orquestração em duas etapas quando a solicitação pede arquivos.

Cenário da batalha naval (06/11/2026): as skills rodavam juntas e o código foi
escrito sem ver o ACESSIBILIDADE.md nem o PLANO_DE_TESTES.md, que já apontavam
os defeitos. Agora as skills que escrevem código rodam depois das outras e
recebem as entregas delas.
"""

import asyncio

from fastapi.testclient import TestClient

from app.agent_catalog.contracts import (
    AgenteEmissor,
    AnaliseEstruturada,
    ArquivoGerado,
    Governanca,
    SkillToolResult,
)
from app.llm.prompts import build_technical_planner_prompt
from app.llm.schemas import LLMPlanRequest
from app.quality_gate.service import evaluate
from app.services import agent_skill_orchestration_service as service
from app.services.artifact_service import check_package, prepare_files
from app.services.team_context import build_team_context, writes_code
from tests.conftest import authenticated_csrf_headers, create_qualified_request, register
from tests.test_background_orchestration import _start_url, _wait_for_status

USER = {"name": "Time de Jogos", "email": "time.jogos@example.com", "password": "StrongPassword!123"}


# --- quem escreve código ------------------------------------------------------


def test_skill_que_entrega_codigo_e_implementadora() -> None:
    assert writes_code({"produced_outputs": ["index.html", "style.css", "game.js"]})
    assert writes_code({"produced_outputs": ["Script de migração (.sql)"]})


def test_skill_que_entrega_documento_ou_analise_nao_e() -> None:
    assert not writes_code({"produced_outputs": ["GDD.md"]})
    assert not writes_code({"produced_outputs": ["Riscos fiscais", "Plano técnico"]})
    assert not writes_code({})


# --- o que o implementador recebe ----------------------------------------------


def test_contexto_do_time_traz_nome_resumo_e_documentos() -> None:
    context = build_team_context(
        [("Game Design", "Regras definidas.", [("GDD.md", "Vitória ao afundar a frota.")])]
    )

    assert "Game Design" in context
    assert "Regras definidas." in context
    assert "GDD.md" in context
    assert "Vitória ao afundar a frota." in context


def test_contexto_do_time_tem_limite_de_tamanho() -> None:
    longo = "x" * 50_000
    context = build_team_context([("QA", "Resumo.", [("PLANO.md", longo)])], max_chars=4000)

    assert len(context) <= 4000


def test_prompt_inclui_as_entregas_do_time() -> None:
    prompt = build_technical_planner_prompt(
        LLMPlanRequest(
            technical_request_id="1",
            trace_id="T",
            title="Jogo",
            problem="Sem código.",
            objective="Gere o código.",
            team_context="[UX] Casas focáveis pelo teclado.",
        )
    )

    assert "Entregas dos outros agentes" in prompt
    assert "Casas focáveis pelo teclado." in prompt


# --- checagem do pacote, sem IA ------------------------------------------------


def test_html_que_carrega_arquivo_que_nao_veio_e_apontado() -> None:
    issues = check_package([("index.html", '<script src="game.js"></script><link href="style.css">')])

    assert any("game.js" in issue for issue in issues)
    assert any("style.css" in issue for issue in issues)


def test_pacote_completo_passa() -> None:
    files = [
        ("index.html", '<link rel="stylesheet" href="style.css"><script src="./game.js"></script>'),
        ("style.css", "body {}"),
        ("game.js", "init()"),
    ]
    assert check_package(files) == []


def test_recursos_externos_e_ancoras_nao_contam() -> None:
    html = (
        '<script src="https://cdn.exemplo.com/x.js"></script>'
        '<a href="#topo">x</a><img src="data:image/png;base64,AA">'
    )
    assert check_package([("index.html", html)]) == []


def test_nome_com_pasta_generated_files_e_limpo() -> None:
    accepted, _ = prepare_files([ArquivoGerado(nome="generated_files/GDD.md", conteudo="# GDD")])

    assert [file.nome for file in accepted] == ["GDD.md"]


def test_quality_gate_aponta_pacote_quebrado() -> None:
    result = SkillToolResult(
        trace_id="T",
        agente_emissor=AgenteEmissor(nome="Programação", dominio="programacao_jogos"),
        analise_estruturada=AnaliseEstruturada(resumo_executivo="Jogo entregue."),
        governanca=Governanca(nivel_confianca="ALTO", justificativa_confianca="ok"),
    )

    verdict = evaluate([result], package_issues=["index.html carrega game.js, que não foi entregue."])

    assert verdict.requires_human_review
    assert any("game.js" in reason for reason in verdict.reasons)


# --- a orquestração em duas etapas ---------------------------------------------


def _create_skill(client: TestClient, name: str, domain: str, outputs: list[str]) -> None:
    response = client.post(
        "/api/v1/agent-skills",
        json={
            "name": name,
            "version": "1.0",
            "author_origin": "Teste",
            "domain": domain,
            "objective": f"Entregar {', '.join(outputs)}.",
            "capabilities": ["Entregar"],
            "expected_inputs": ["Solicitação"],
            "produced_outputs": outputs,
            "operating_limits": ["Só propostas"],
            "input_contract_ref": "solicitacao_analise_schema.v1",
            "output_contract_ref": "resposta_especialista_schema.v1",
            "validation_criteria": ["Contrato válido"],
        },
        headers=authenticated_csrf_headers(client),
    )
    assert response.status_code == 201, response.text


def _spy(monkeypatch) -> list:
    calls: list = []

    async def fake(skill, tool_call) -> SkillToolResult:
        calls.append((skill.name, tool_call.team_context))
        await asyncio.sleep(0.05)
        files = (
            [ArquivoGerado(nome="ACESSIBILIDADE.md", conteudo="Jogar só com teclado.")]
            if skill.name == "UX"
            else [ArquivoGerado(nome="index.html", conteudo="<p>jogo</p>")]
        )
        return SkillToolResult(
            trace_id=tool_call.trace_id,
            agente_emissor=AgenteEmissor(nome=skill.name, dominio=skill.domain),
            analise_estruturada=AnaliseEstruturada(resumo_executivo=f"Resumo de {skill.name}."),
            governanca=Governanca(nivel_confianca="ALTO", justificativa_confianca="ok"),
            arquivos=files,
        )

    monkeypatch.setattr(service, "call_skill_tool", fake)
    return calls


def _run(client: TestClient, objective: str) -> dict:
    request = create_qualified_request(
        client,
        title="Criar um jogo de batalha naval",
        problem="Ainda não existe nenhum código do jogo.",
        objective=objective,
    )
    started = client.post(_start_url(request["id"]), headers=authenticated_csrf_headers(client))
    assert started.status_code == 202
    _wait_for_status(client, request["id"], "COMPLETED", "VALIDATING", "FAILED")
    return request


def test_com_pedido_de_codigo_o_implementador_roda_depois_e_recebe_as_entregas(
    client: TestClient, monkeypatch
) -> None:
    register(client, USER)
    _create_skill(client, "Programação", "programacao_jogos", ["index.html", "game.js"])
    _create_skill(client, "UX", "ux_jogos", ["ACESSIBILIDADE.md"])
    calls = _spy(monkeypatch)

    request = _run(client, "Gere o código-fonte do jogo em index.html e game.js.")

    assert [name for name, _ in calls] == ["UX", "Programação"]
    assert calls[0][1] is None
    assert "Jogar só com teclado." in calls[1][1]
    events = client.get(f"/api/v1/orchestrations/{request['trace_id']}").json()["events"]
    shared = [event for event in events if event["event_type"] == "TEAM_CONTEXT_SHARED"]
    assert len(shared) == 1
    assert shared[0]["payload"]["implementers"] == ["Programação"]


def test_sem_pedido_de_arquivos_todas_rodam_juntas_sem_contexto(client: TestClient, monkeypatch) -> None:
    register(client, USER)
    _create_skill(client, "Programação", "programacao_jogos", ["index.html", "game.js"])
    _create_skill(client, "UX", "ux_jogos", ["ACESSIBILIDADE.md"])
    calls = _spy(monkeypatch)

    _run(client, "Avaliar riscos do projeto do jogo.")

    assert sorted(name for name, _ in calls) == ["Programação", "UX"]
    assert all(context is None for _, context in calls)


def test_so_implementadores_rodam_juntos_como_antes(client: TestClient, monkeypatch) -> None:
    register(client, USER)
    _create_skill(client, "Programação", "programacao_jogos", ["index.html", "game.js"])
    calls = _spy(monkeypatch)

    _run(client, "Gere o código-fonte do jogo em index.html e game.js.")

    assert calls == [("Programação", None)]
