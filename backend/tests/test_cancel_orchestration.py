import asyncio
import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.database import SessionLocal
from app.models import AgentSkillInvocation, TechnicalRequest
from app.services import agent_skill_orchestration_service as service
from tests.conftest import authenticated_csrf_headers, create_qualified_request, register
from tests.test_background_orchestration import _fake_skill_tool, _start_url, _wait_for_status
from tests.test_clan_orchestration import OTHER, OWNER, _switch_user
from tests.test_human_review import FIXTURE_MANIFEST


def _headers(client: TestClient) -> dict[str, str]:
    return authenticated_csrf_headers(client)


def _cancel_url(request_id: str) -> str:
    return f"/api/v1/agent-skills/requests/{request_id}/cancel"


def _prepare(client: TestClient) -> dict:
    register(client, OWNER)
    client.post(
        "/api/v1/agent-skills/import", json={"manifest_markdown": FIXTURE_MANIFEST}, headers=_headers(client)
    )
    return create_qualified_request(client)


@pytest.fixture
def slow_skill(monkeypatch: pytest.MonkeyPatch) -> dict:
    """Skill que demora: dá tempo de interromper no meio. Marca se chegou ao fim."""
    state = {"started": False, "finished": False}

    async def slow(skill, tool_call):
        state["started"] = True
        await asyncio.sleep(5)
        state["finished"] = True
        return await _fake_skill_tool(skill, tool_call)

    monkeypatch.setattr(service, "call_skill_tool", slow)
    return state


def _wait(predicate, timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.05)
    raise AssertionError("A condição não foi atingida a tempo.")


def _start_and_wait_for_skill(client: TestClient, technical_request: dict, slow_skill: dict) -> None:
    assert client.post(_start_url(technical_request["id"]), headers=_headers(client)).status_code == 202
    _wait(lambda: slow_skill["started"])


def test_running_orchestration_can_be_interrupted(client: TestClient, slow_skill) -> None:
    technical_request = _prepare(client)
    _start_and_wait_for_skill(client, technical_request, slow_skill)

    response = client.post(_cancel_url(technical_request["id"]), headers=_headers(client))

    assert response.status_code == 202
    finished = _wait_for_status(client, technical_request["id"], "CANCELLED")
    assert finished["consolidated_response"] is None
    assert slow_skill["finished"] is False


def test_interruption_is_recorded_in_the_timeline(client: TestClient, slow_skill) -> None:
    technical_request = _prepare(client)
    _start_and_wait_for_skill(client, technical_request, slow_skill)

    client.post(_cancel_url(technical_request["id"]), headers=_headers(client))
    _wait_for_status(client, technical_request["id"], "CANCELLED")

    events = client.get(f"/api/v1/orchestrations/{technical_request['trace_id']}").json()["events"]
    cancelled = [event for event in events if event["event_type"] == "ORCHESTRATION_CANCELLED"]
    assert len(cancelled) == 1
    assert cancelled[0]["actor"] == "USER"


def test_unfinished_skill_calls_are_marked_as_cancelled(client: TestClient, slow_skill) -> None:
    technical_request = _prepare(client)
    _start_and_wait_for_skill(client, technical_request, slow_skill)

    client.post(_cancel_url(technical_request["id"]), headers=_headers(client))
    _wait_for_status(client, technical_request["id"], "CANCELLED")

    with SessionLocal() as db:
        statuses = list(
            db.scalars(
                select(AgentSkillInvocation.status).where(
                    AgentSkillInvocation.technical_request_id == technical_request["id"]
                )
            )
        )
    assert statuses == ["CANCELLED"]


def test_after_interrupting_the_context_can_be_completed_and_run_again(
    client: TestClient, slow_skill, monkeypatch
) -> None:
    technical_request = _prepare(client)
    _start_and_wait_for_skill(client, technical_request, slow_skill)
    client.post(_cancel_url(technical_request["id"]), headers=_headers(client))
    _wait_for_status(client, technical_request["id"], "CANCELLED")

    completed = client.post(
        f"/api/v1/requests/{technical_request['id']}/context",
        json={"context": "Sistema legado em Java. Faltava dizer que o job roda toda madrugada."},
        headers=_headers(client),
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "QUALIFIED"

    monkeypatch.setattr(service, "call_skill_tool", _fake_skill_tool)
    assert client.post(_start_url(technical_request["id"]), headers=_headers(client)).status_code == 202
    assert _wait_for_status(client, technical_request["id"], "COMPLETED", "VALIDATING")[
        "consolidated_response"
    ]


def test_cancelled_request_can_run_again_without_changes(client: TestClient, slow_skill, monkeypatch) -> None:
    technical_request = _prepare(client)
    _start_and_wait_for_skill(client, technical_request, slow_skill)
    client.post(_cancel_url(technical_request["id"]), headers=_headers(client))
    _wait_for_status(client, technical_request["id"], "CANCELLED")

    monkeypatch.setattr(service, "call_skill_tool", _fake_skill_tool)

    assert client.post(_start_url(technical_request["id"]), headers=_headers(client)).status_code == 202


def test_only_a_running_orchestration_can_be_interrupted(client: TestClient) -> None:
    technical_request = _prepare(client)

    response = client.post(_cancel_url(technical_request["id"]), headers=_headers(client))

    assert response.status_code == 409


def test_other_person_cannot_interrupt(client: TestClient, slow_skill) -> None:
    technical_request = _prepare(client)
    _start_and_wait_for_skill(client, technical_request, slow_skill)
    _switch_user(client, OTHER)

    response = client.post(_cancel_url(technical_request["id"]), headers=_headers(client))

    assert response.status_code == 404


def test_run_lost_by_a_restart_is_cancelled_right_away(client: TestClient) -> None:
    technical_request = _prepare(client)
    with SessionLocal() as db:
        db.get(TechnicalRequest, technical_request["id"]).status = "RUNNING"
        db.commit()

    response = client.post(_cancel_url(technical_request["id"]), headers=_headers(client))

    assert response.status_code == 202
    assert client.get(f"/api/v1/requests/{technical_request['id']}").json()["status"] == "CANCELLED"


def test_context_cannot_change_while_the_orchestration_runs(client: TestClient, slow_skill) -> None:
    technical_request = _prepare(client)
    _start_and_wait_for_skill(client, technical_request, slow_skill)

    response = client.post(
        f"/api/v1/requests/{technical_request['id']}/context",
        json={"context": "Contexto novo enviado no meio da execução da análise."},
        headers=_headers(client),
    )

    assert response.status_code == 409
    assert client.get(f"/api/v1/requests/{technical_request['id']}").json()["status"] == "RUNNING"
    client.post(_cancel_url(technical_request["id"]), headers=_headers(client))
    _wait_for_status(client, technical_request["id"], "CANCELLED")
