"""Comitê que não usa a base global e anexos contados como evidência.

Teste de 23/11/2026: no Comitê Jurídico, a busca trouxe trechos da base de exemplo
(o sistema fictício de limite de crédito) e o relator citou um "risco LGPD" sem
relação com o processo. Comitês de fora do software desligam a base global e contam
com os documentos anexados e os repositórios deles.
"""

from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.agent_catalog import tool_interface
from app.agent_catalog.contracts import SkillToolCall
from app.agent_catalog.tool_interface import SkillExecutor
from app.core.database import SessionLocal
from app.models import AgentSkill, KnowledgeChunk, TechnicalRequest, User
from app.rag.retriever import InMemoryVectorRetriever
from tests.conftest import authenticated_csrf_headers, register
from tests.test_clan_orchestration import OTHER, OWNER, _clan, _switch_user
from tests.test_skill_suggestions import WordCountEmbeddings
from tests.test_team_context import _create_skill


def _settings(client: TestClient, clan_id: str, **changes):
    return client.patch(
        f"/api/v1/clans/{clan_id}/settings", json=changes, headers=authenticated_csrf_headers(client)
    )


# --- a opção no comitê -----------------------------------------------------------


def test_comite_usa_a_base_global_por_padrao(client: TestClient) -> None:
    register(client, OWNER)

    clan = _clan(client)

    assert clan["use_global_knowledge"] is True
    listed = next(c for c in client.get("/api/v1/clans").json() if c["id"] == clan["id"])
    assert listed["use_global_knowledge"] is True


def test_comite_pode_nascer_sem_a_base_global(client: TestClient) -> None:
    register(client, OWNER)

    clan = _clan(client, use_global_knowledge=False)

    assert clan["use_global_knowledge"] is False


def test_so_o_dono_liga_e_desliga_a_base_global(client: TestClient) -> None:
    register(client, OWNER)
    clan = _clan(client, is_open=True)

    response = _settings(client, clan["id"], use_global_knowledge=False)
    assert response.status_code == 200
    assert response.json()["use_global_knowledge"] is False

    _switch_user(client, OTHER)
    client.post(f"/api/v1/clans/{clan['id']}/join", headers=authenticated_csrf_headers(client))
    assert _settings(client, clan["id"], use_global_knowledge=True).status_code == 403


# --- a busca ------------------------------------------------------------------------


def _chunk(db, embeddings, name: str, text: str, clan_id: str | None) -> None:
    db.add(
        KnowledgeChunk(
            artifact_name=name,
            source_type="teste",
            content=text,
            embedding=embeddings.embed([text])[0],
            clan_id=clan_id,
            chunk_index=0,
            char_start=0,
            char_end=len(text),
        )
    )


def test_sem_a_base_global_a_busca_ve_so_o_comite(client: TestClient) -> None:
    register(client, OWNER)
    clan = _clan(client)
    embeddings = WordCountEmbeddings()
    with SessionLocal() as db:
        _chunk(db, embeddings, "global:credito.md", "multa contrato limite de crédito", None)
        _chunk(db, embeddings, "comite:lei.md", "multa contrato de adesão abusiva", clan["id"])
        db.commit()

        retriever = InMemoryVectorRetriever(db, embeddings)
        com_global = retriever.retrieve("multa contrato", top_k=5, clan_id=clan["id"])
        sem_global = retriever.retrieve("multa contrato", top_k=5, clan_id=clan["id"], include_global=False)

    assert {c.artifact_name for c in com_global} == {"global:credito.md", "comite:lei.md"}
    assert [c.artifact_name for c in sem_global] == ["comite:lei.md"]


# --- anexos como evidência ---------------------------------------------------------


def _plan(monkeypatch, missing: list[str] | None = None) -> None:
    def fake_plan(db, **kwargs):
        return SimpleNamespace(
            llm_call_id="sem-trechos",
            plan=SimpleNamespace(
                summary="A multa é abusiva.",
                risks=["Multa de 50% desproporcional"],
                missing_information=missing or [],
                generated_files=[],
            ),
        )

    monkeypatch.setattr(tool_interface, "generate_technical_plan", fake_plan)


def _execute(client: TestClient, monkeypatch, *, anexos: dict[str, str], missing: list[str] | None = None):
    register(client, OWNER)
    clan = _clan(client, use_global_knowledge=False)
    _create_skill(client, "Advogado", "Direito", ["Parecer jurídico"])
    request = client.post(
        "/api/v1/requests",
        json={
            "title": "Ação contra academia",
            "problem": "Consumidora cobrada em multa de 50% após cancelar o plano anual.",
            "objective": "Avaliar os pontos fortes e fracos de cada parte.",
            "context": "Contrato de adesão assinado em janeiro, cancelamento pedido por e-mail em abril.",
            "restrictions": [],
            "requested_domains": [],
            "clan_id": clan["id"],
        },
        headers=authenticated_csrf_headers(client),
    ).json()
    for nome, texto in anexos.items():
        response = client.post(
            f"/api/v1/requests/{request['id']}/attachments",
            files={"file": (nome, texto.encode("utf-8"), "text/plain")},
            headers=authenticated_csrf_headers(client),
        )
        assert response.status_code == 201, response.text
    _plan(monkeypatch, missing)

    with SessionLocal() as db:
        technical_request = db.get(TechnicalRequest, request["id"])
        skill = db.scalar(select(AgentSkill).where(AgentSkill.name == "Advogado"))
        user = db.scalar(select(User).where(User.email == OWNER["email"]))
        call = SkillToolCall(
            trace_id=technical_request.trace_id,
            technical_request_id=technical_request.id,
            user_id=user.id,
            agent_skill_id=skill.id,
        )
        return SkillExecutor().execute(
            db, skill=skill, technical_request=technical_request, user=user, tool_call=call
        )


def test_documento_anexado_conta_como_evidencia(client: TestClient, monkeypatch) -> None:
    result = _execute(client, monkeypatch, anexos={"contrato.txt": "Cláusula 9: multa de 50%."})

    assert result.governanca.nivel_confianca == "ALTO"
    finding = result.analise_estruturada.descobertas_tecnicas[0]
    assert finding.item_identificado == "contrato.txt"
    assert "Cláusula 9" in finding.trecho_referenciado
    assert "anexado" in result.governanca.justificativa_confianca


def test_anexo_com_lacunas_fica_medio(client: TestClient, monkeypatch) -> None:
    result = _execute(
        client, monkeypatch, anexos={"contrato.txt": "Cláusula 9."}, missing=["Data da negativação"]
    )

    assert result.governanca.nivel_confianca == "MEDIO"


def test_sem_anexo_nem_trecho_a_confianca_continua_baixa(client: TestClient, monkeypatch) -> None:
    result = _execute(client, monkeypatch, anexos={})

    assert result.governanca.nivel_confianca == "BAIXO"
