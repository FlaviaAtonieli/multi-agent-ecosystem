import time

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.agent_catalog.contracts import AgenteEmissor, AnaliseEstruturada, Governanca, SkillToolResult
from app.core.database import SessionLocal
from app.models import AuditLog, TechnicalRequest
from app.services import agent_skill_orchestration_service as service
from tests.conftest import authenticated_csrf_headers, create_qualified_request, register
from tests.test_human_review import FIXTURE_MANIFEST

USER = {
    "name": "Tecnica Segundo Plano",
    "email": "tecnica.segundoplano@example.com",
    "password": "StrongPassword!123",
}
OTHER_USER = {
    "name": "Outra Pessoa",
    "email": "outra.pessoa@example.com",
    "password": "StrongPassword!123",
}


async def _fake_skill_tool(skill, tool_call) -> SkillToolResult:
    return SkillToolResult(
        trace_id=tool_call.trace_id,
        agente_emissor=AgenteEmissor(nome=skill.name, dominio=skill.domain),
        analise_estruturada=AnaliseEstruturada(resumo_executivo="Resumo da análise."),
        governanca=Governanca(nivel_confianca="ALTO", justificativa_confianca="Evidência suficiente."),
    )


def _start_url(request_id: str) -> str:
    return f"/api/v1/agent-skills/requests/{request_id}/start"


def _prepare_request(client: TestClient) -> dict:
    register(client, USER)
    client.post(
        "/api/v1/agent-skills/import",
        json={"manifest_markdown": FIXTURE_MANIFEST},
        headers=authenticated_csrf_headers(client),
    )
    return create_qualified_request(client, requested_domains=["codigo_legado"])


def _wait_for_status(client: TestClient, request_id: str, *expected: str) -> dict:
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        body = client.get(f"/api/v1/requests/{request_id}").json()
        if body["status"] in expected:
            return body
        time.sleep(0.05)
    raise AssertionError(f"Solicitação não chegou a {expected}; último status: {body['status']}")


def test_start_runs_orchestration_in_background(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(service, "call_skill_tool", _fake_skill_tool)
    technical_request = _prepare_request(client)

    response = client.post(_start_url(technical_request["id"]), headers=authenticated_csrf_headers(client))

    assert response.status_code == 202
    assert response.json() == {"trace_id": technical_request["trace_id"], "status": "RUNNING"}

    finished = _wait_for_status(client, technical_request["id"], "COMPLETED", "VALIDATING")
    assert finished["consolidated_response"] is not None

    events = client.get(f"/api/v1/orchestrations/{technical_request['trace_id']}").json()["events"]
    started = [event for event in events if event["event_type"] == "ORCHESTRATION_EXECUTION_STARTED"]
    assert started[0]["payload"] == {"total_skills": 1, "max_parallel": 3}
    assert any(event["event_type"] == "AGENT_SKILL_INVOCATION_COMPLETED" for event in events)

    with SessionLocal() as db:
        audit = db.scalar(select(AuditLog).where(AuditLog.event_type == "AGENT_SKILL_ORCHESTRATION_STARTED"))
        assert audit is not None


def test_start_rejects_request_already_running(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.v1.endpoints.agent_skills.start_orchestration_in_background", lambda **_: None
    )
    technical_request = _prepare_request(client)

    first = client.post(_start_url(technical_request["id"]), headers=authenticated_csrf_headers(client))
    second = client.post(_start_url(technical_request["id"]), headers=authenticated_csrf_headers(client))

    assert first.status_code == 202
    assert second.status_code == 409


def test_start_marks_request_failed_on_unexpected_error_and_allows_retry(
    client: TestClient, monkeypatch
) -> None:
    async def _broken_step(*_, **__):
        raise RuntimeError("falha inesperada")

    monkeypatch.setattr(service, "execute_orchestration_step", _broken_step)
    technical_request = _prepare_request(client)

    response = client.post(_start_url(technical_request["id"]), headers=authenticated_csrf_headers(client))
    assert response.status_code == 202
    _wait_for_status(client, technical_request["id"], "FAILED")

    events = client.get(f"/api/v1/orchestrations/{technical_request['trace_id']}").json()["events"]
    failure = next(event for event in events if event["event_type"] == "ORCHESTRATION_EXECUTION_FAILED")
    assert "falha inesperada" not in failure["message"]

    monkeypatch.undo()
    monkeypatch.setattr(service, "call_skill_tool", _fake_skill_tool)
    retry = client.post(_start_url(technical_request["id"]), headers=authenticated_csrf_headers(client))
    assert retry.status_code == 202
    _wait_for_status(client, technical_request["id"], "COMPLETED", "VALIDATING")


def test_start_is_scoped_to_request_owner(client: TestClient) -> None:
    technical_request = _prepare_request(client)
    client.post("/api/v1/auth/logout", headers=authenticated_csrf_headers(client))
    register(client, OTHER_USER)

    response = client.post(_start_url(technical_request["id"]), headers=authenticated_csrf_headers(client))

    assert response.status_code == 404


def test_start_without_compatible_skills_returns_conflict(client: TestClient) -> None:
    register(client, USER)
    technical_request = create_qualified_request(client, requested_domains=["codigo_legado"])

    response = client.post(_start_url(technical_request["id"]), headers=authenticated_csrf_headers(client))

    assert response.status_code == 409
    assert client.get(f"/api/v1/requests/{technical_request['id']}").json()["status"] == "QUALIFIED"


def test_startup_marks_interrupted_runs_as_failed(client: TestClient) -> None:
    technical_request = _prepare_request(client)

    with SessionLocal() as db:
        row = db.get(TechnicalRequest, technical_request["id"])
        row.status = "RUNNING"
        db.commit()

    with SessionLocal() as db:
        assert service.fail_interrupted_orchestrations(db) == 1
        assert service.fail_interrupted_orchestrations(db) == 0

    assert client.get(f"/api/v1/requests/{technical_request['id']}").json()["status"] == "FAILED"
