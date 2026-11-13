import time

from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.models import TechnicalRequest
from app.services import agent_skill_orchestration_service as service
from app.services import follow_up_service
from tests.conftest import authenticated_csrf_headers, create_qualified_request, register
from tests.test_background_orchestration import _fake_skill_tool
from tests.test_human_review import FIXTURE_MANIFEST

USER = {
    "name": "Tecnica Pergunta",
    "email": "tecnica.pergunta@example.com",
    "password": "StrongPassword!123",
}
QUESTION = {"question": "Qual é o maior risco desta mudança?", "target_domain": "codigo_legado"}


def _executed_request(client: TestClient, monkeypatch) -> dict:
    monkeypatch.setattr(service, "call_skill_tool", _fake_skill_tool)
    register(client, USER)
    client.post(
        "/api/v1/agent-skills/import",
        json={"manifest_markdown": FIXTURE_MANIFEST},
        headers=authenticated_csrf_headers(client),
    )
    technical_request = create_qualified_request(client, requested_domains=["codigo_legado"])
    response = client.post(
        f"/api/v1/agent-skills/requests/{technical_request['id']}/execute",
        headers=authenticated_csrf_headers(client),
    )
    assert response.status_code == 200
    return technical_request


def _start_url(request_id: str) -> str:
    return f"/api/v1/agent-skills/requests/{request_id}/ask/start"


def _events(client: TestClient, technical_request: dict) -> list[dict]:
    return client.get(f"/api/v1/orchestrations/{technical_request['trace_id']}").json()["events"]


def _wait_for_event(client: TestClient, technical_request: dict, event_type: str) -> dict:
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        for event in _events(client, technical_request):
            if event["event_type"] == event_type:
                return event
        time.sleep(0.05)
    raise AssertionError(f"Evento {event_type} não apareceu.")


def test_start_follow_up_answers_in_background(client: TestClient, monkeypatch) -> None:
    technical_request = _executed_request(client, monkeypatch)

    response = client.post(
        _start_url(technical_request["id"]), json=QUESTION, headers=authenticated_csrf_headers(client)
    )

    assert response.status_code == 202
    _wait_for_event(client, technical_request, "FOLLOW_UP_RESPONSE_RECEIVED")
    exchanges = client.get(f"/api/v1/orchestrations/{technical_request['trace_id']}/follow-ups").json()
    assert [exchange["question"] for exchange in exchanges] == [QUESTION["question"]]


def test_start_follow_up_rejects_while_another_is_pending(client: TestClient, monkeypatch) -> None:
    technical_request = _executed_request(client, monkeypatch)
    monkeypatch.setattr(
        "app.api.v1.endpoints.agent_skills.start_follow_up_in_background", lambda **_: None
    )

    first = client.post(
        _start_url(technical_request["id"]), json=QUESTION, headers=authenticated_csrf_headers(client)
    )
    second = client.post(
        _start_url(technical_request["id"]), json=QUESTION, headers=authenticated_csrf_headers(client)
    )

    assert first.status_code == 202
    assert second.status_code == 409


def test_start_follow_up_records_unexpected_failure_and_allows_retry(client: TestClient, monkeypatch) -> None:
    technical_request = _executed_request(client, monkeypatch)

    async def _broken_answer(*_, **__):
        raise RuntimeError("falha inesperada")

    with monkeypatch.context() as patch:
        patch.setattr(follow_up_service, "_answer_follow_up", _broken_answer)
        response = client.post(
            _start_url(technical_request["id"]), json=QUESTION, headers=authenticated_csrf_headers(client)
        )
        assert response.status_code == 202
        failure = _wait_for_event(client, technical_request, "FOLLOW_UP_FAILED")
    assert "falha inesperada" not in failure["message"]

    retry = client.post(
        _start_url(technical_request["id"]), json=QUESTION, headers=authenticated_csrf_headers(client)
    )
    assert retry.status_code == 202


def test_start_follow_up_requires_prior_execution(client: TestClient) -> None:
    register(client, USER)
    technical_request = create_qualified_request(client)

    response = client.post(
        _start_url(technical_request["id"]), json=QUESTION, headers=authenticated_csrf_headers(client)
    )

    assert response.status_code == 409


def test_startup_fails_interrupted_follow_ups(client: TestClient, monkeypatch) -> None:
    technical_request = _executed_request(client, monkeypatch)

    with SessionLocal() as db:
        row = db.get(TechnicalRequest, technical_request["id"])
        follow_up_service.record_follow_up_question(
            db, row, question=QUESTION["question"], target_domain=None
        )
        assert follow_up_service.has_pending_follow_up(db, row) is True
        assert follow_up_service.fail_interrupted_follow_ups(db) == 1
        assert follow_up_service.has_pending_follow_up(db, row) is False
        assert follow_up_service.fail_interrupted_follow_ups(db) == 0
