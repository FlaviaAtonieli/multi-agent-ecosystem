import asyncio

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent_catalog.contracts import AgenteEmissor, AnaliseEstruturada, Governanca, SkillToolResult
from app.core.config import settings
from app.core.database import SessionLocal
from app.models import OrchestrationEvent, TechnicalRequest
from app.services import agent_skill_orchestration_service as service
from app.services.orchestration_service import append_event
from tests.conftest import authenticated_csrf_headers, create_qualified_request, register
from tests.test_human_review import FIXTURE_MANIFEST

USER = {
    "name": "Tecnica Paralelo",
    "email": "tecnica.paralelo@example.com",
    "password": "StrongPassword!123",
}
DOMAINS = ["codigo_legado", "regras_negocio", "qualidade_testes", "apis_integracoes", "dados_privacidade"]


def _register_skills(client: TestClient) -> None:
    register(client, USER)
    for domain in DOMAINS:
        manifest = FIXTURE_MANIFEST.replace(
            "Domínio de atuação: Código Legado", f"Domínio de atuação: {domain}"
        )
        response = client.post(
            "/api/v1/agent-skills/import",
            json={"manifest_markdown": manifest},
            headers=authenticated_csrf_headers(client),
        )
        assert response.status_code == 201


def _result_for(skill, tool_call) -> SkillToolResult:
    return SkillToolResult(
        trace_id=tool_call.trace_id,
        agente_emissor=AgenteEmissor(nome=skill.name, dominio=skill.domain),
        analise_estruturada=AnaliseEstruturada(resumo_executivo=f"Resumo de {skill.domain}."),
        governanca=Governanca(nivel_confianca="ALTO", justificativa_confianca="Evidência suficiente."),
    )


def test_skills_run_concurrently_up_to_the_limit_and_keep_their_order(
    client: TestClient, monkeypatch
) -> None:
    running = 0
    peak = 0
    # Reverse delays: the first skill requested is the last one to finish.
    delays = dict(zip(DOMAINS, [0.25, 0.2, 0.15, 0.1, 0.05], strict=True))

    async def fake_skill_tool(skill, tool_call) -> SkillToolResult:
        nonlocal running, peak
        running += 1
        peak = max(peak, running)
        await asyncio.sleep(delays[skill.domain])
        running -= 1
        return _result_for(skill, tool_call)

    monkeypatch.setattr(service, "call_skill_tool", fake_skill_tool)
    monkeypatch.setattr(settings, "orchestration_max_parallel_skills", 2)
    _register_skills(client)
    technical_request = create_qualified_request(client, requested_domains=DOMAINS)

    response = client.post(
        f"/api/v1/agent-skills/requests/{technical_request['id']}/execute",
        headers=authenticated_csrf_headers(client),
    )

    assert response.status_code == 200
    assert peak == 2
    assert [item["agente_emissor"]["dominio"] for item in response.json()["results"]] == DOMAINS


def test_one_failing_skill_does_not_stop_the_others(client: TestClient, monkeypatch) -> None:
    async def fake_skill_tool(skill, tool_call) -> SkillToolResult:
        if skill.domain == "regras_negocio":
            raise RuntimeError("falha só nesta skill")
        return _result_for(skill, tool_call)

    monkeypatch.setattr(service, "call_skill_tool", fake_skill_tool)
    _register_skills(client)
    technical_request = create_qualified_request(client, requested_domains=DOMAINS)

    response = client.post(
        f"/api/v1/agent-skills/requests/{technical_request['id']}/execute",
        headers=authenticated_csrf_headers(client),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["invocations_count"] == len(DOMAINS)
    assert "regras_negocio" not in [item["agente_emissor"]["dominio"] for item in body["results"]]
    assert len(body["results"]) == len(DOMAINS) - 1


def test_append_event_retries_after_sequence_collision(client: TestClient, monkeypatch) -> None:
    """Reproduces what two skill processes do: both read the same max sequence."""
    register(client, USER)
    technical_request = create_qualified_request(client)

    with SessionLocal() as db:
        row = db.get(TechnicalRequest, technical_request["id"])
        current_max = db.scalar(
            select(OrchestrationEvent.sequence_number)
            .where(OrchestrationEvent.technical_request_id == row.id)
            .order_by(OrchestrationEvent.sequence_number.desc())
        )

        real_scalar = Session.scalar
        calls = {"count": 0}

        def stale_first_read(self, statement, *args, **kwargs):
            calls["count"] += 1
            if calls["count"] == 1:
                return current_max - 1
            return real_scalar(self, statement, *args, **kwargs)

        monkeypatch.setattr(Session, "scalar", stale_first_read)
        event = append_event(
            db,
            row,
            event_type="TEST_EVENT",
            actor="TEST",
            title="Evento de teste",
            message="Colisão de numeração.",
        )
        db.commit()
        monkeypatch.undo()

        assert calls["count"] == 2
        assert event.sequence_number == current_max + 1
