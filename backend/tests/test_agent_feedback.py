"""Avaliação humana da resposta de cada agente (útil ou não útil, com motivo)."""

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core.config import settings
from app.core.database import SessionLocal
from app.models import AgentResponseFeedback, AuditLog
from tests.conftest import authenticated_csrf_headers
from tests.test_clan_orchestration import OTHER, _switch_user
from tests.test_metrics import _metric_value
from tests.test_skill_artifacts import _run_with_files


def _results(client: TestClient, request: dict) -> list[dict]:
    response = client.get(f"/api/v1/orchestrations/{request['trace_id']}/skill-results")
    assert response.status_code == 200
    return response.json()


def _feedback_url(request: dict, invocation_id: str) -> str:
    return f"/api/v1/orchestrations/{request['trace_id']}/skill-results/{invocation_id}/feedback"


def _rate(client: TestClient, request: dict, invocation_id: str, body: dict):
    return client.put(
        _feedback_url(request, invocation_id), json=body, headers=authenticated_csrf_headers(client)
    )


def _executed(client: TestClient, monkeypatch) -> tuple[dict, str]:
    request = _run_with_files(client, monkeypatch)
    return request, _results(client, request)[0]["id"]


def test_resposta_comeca_sem_avaliacao(client: TestClient, monkeypatch) -> None:
    request, _ = _executed(client, monkeypatch)

    assert _results(client, request)[0]["feedback"] is None


def test_marcar_como_util_aparece_no_resultado(client: TestClient, monkeypatch) -> None:
    request, invocation_id = _executed(client, monkeypatch)

    response = _rate(client, request, invocation_id, {"useful": True})

    assert response.status_code == 200
    assert response.json()["useful"] is True
    assert response.json()["reason"] is None
    assert _results(client, request)[0]["feedback"]["useful"] is True


def test_nao_util_guarda_motivo_e_comentario(client: TestClient, monkeypatch) -> None:
    request, invocation_id = _executed(client, monkeypatch)

    response = _rate(
        client,
        request,
        invocation_id,
        {"useful": False, "reason": "SEM_EVIDENCIA", "comment": "Não citou o módulo de faturamento."},
    )

    assert response.status_code == 200
    feedback = _results(client, request)[0]["feedback"]
    assert feedback == {
        "useful": False,
        "reason": "SEM_EVIDENCIA",
        "comment": "Não citou o módulo de faturamento.",
        "updated_at": feedback["updated_at"],
    }


def test_trocar_a_avaliacao_substitui_a_anterior(client: TestClient, monkeypatch) -> None:
    request, invocation_id = _executed(client, monkeypatch)
    _rate(client, request, invocation_id, {"useful": False, "reason": "INCOMPLETA", "comment": "Faltou X."})

    _rate(client, request, invocation_id, {"useful": True})

    assert _results(client, request)[0]["feedback"]["useful"] is True
    assert _results(client, request)[0]["feedback"]["reason"] is None
    assert _results(client, request)[0]["feedback"]["comment"] is None
    with SessionLocal() as db:
        assert db.scalar(select(func.count(AgentResponseFeedback.id))) == 1


def test_nao_util_exige_motivo(client: TestClient, monkeypatch) -> None:
    request, invocation_id = _executed(client, monkeypatch)

    assert _rate(client, request, invocation_id, {"useful": False}).status_code == 422


def test_util_nao_aceita_motivo(client: TestClient, monkeypatch) -> None:
    request, invocation_id = _executed(client, monkeypatch)

    assert _rate(client, request, invocation_id, {"useful": True, "reason": "INCORRETA"}).status_code == 422


def test_motivo_fora_da_lista_e_recusado(client: TestClient, monkeypatch) -> None:
    request, invocation_id = _executed(client, monkeypatch)

    assert _rate(client, request, invocation_id, {"useful": False, "reason": "CHATA"}).status_code == 422


def test_remover_a_avaliacao(client: TestClient, monkeypatch) -> None:
    request, invocation_id = _executed(client, monkeypatch)
    _rate(client, request, invocation_id, {"useful": True})
    headers = authenticated_csrf_headers(client)

    assert client.delete(_feedback_url(request, invocation_id), headers=headers).status_code == 204
    assert _results(client, request)[0]["feedback"] is None
    # Remover de novo não é erro: o resultado é o mesmo.
    assert client.delete(_feedback_url(request, invocation_id), headers=headers).status_code == 204


def test_exige_csrf(client: TestClient, monkeypatch) -> None:
    request, invocation_id = _executed(client, monkeypatch)

    assert client.put(_feedback_url(request, invocation_id), json={"useful": True}).status_code == 403


def test_resposta_de_outra_solicitacao_nao_existe(client: TestClient, monkeypatch) -> None:
    request, _ = _executed(client, monkeypatch)

    assert _rate(client, request, "nao-existe", {"useful": True}).status_code == 404


def test_outra_pessoa_nao_avalia(client: TestClient, monkeypatch) -> None:
    request, invocation_id = _executed(client, monkeypatch)
    client.post("/api/v1/auth/register", json=OTHER, headers=authenticated_csrf_headers(client))
    _switch_user(client, OTHER)

    assert _rate(client, request, invocation_id, {"useful": True}).status_code == 404


def test_auditoria_registra_a_avaliacao_sem_o_comentario(client: TestClient, monkeypatch) -> None:
    request, invocation_id = _executed(client, monkeypatch)

    _rate(
        client, request, invocation_id, {"useful": False, "reason": "INCORRETA", "comment": "TEXTO-PRIVADO"}
    )

    with SessionLocal() as db:
        event = db.scalar(select(AuditLog).where(AuditLog.event_type == "AGENT_RESPONSE_RATED"))
    assert event is not None
    assert event.details["invocation_id"] == invocation_id
    assert event.details["useful"] is False
    assert event.details["reason"] == "INCORRETA"
    assert "TEXTO-PRIVADO" not in str(event.details)


def test_metrica_conta_por_area_confianca_e_quality_gate(client: TestClient, monkeypatch) -> None:
    request, invocation_id = _executed(client, monkeypatch)
    labels = {"domain": "codigo_legado", "confidence": "ALTO", "useful": "false"}

    _rate(client, request, invocation_id, {"useful": False, "reason": "INCOMPLETA"})

    text = client.get("/metrics").text
    assert _metric_value(text, "agenthub_agent_response_feedback", **labels, quality_gate="approved") == 1
    assert _metric_value(text, "agenthub_agent_response_feedback", **labels, quality_gate="human_review") == 0


def test_cors_libera_put_para_o_frontend_em_outra_origem(client: TestClient) -> None:
    # Em desenvolvimento o frontend roda em outra porta; sem PUT na lista, o navegador
    # barra a avaliação e a edição de skill antes de chegar à API.
    origin = settings.cors_origin_list[0]
    response = client.options(
        "/api/v1/orchestrations/TRC-1/skill-results/inv-1/feedback",
        headers={"Origin": origin, "Access-Control-Request-Method": "PUT"},
    )

    assert response.status_code == 200
    assert "PUT" in response.headers["access-control-allow-methods"]
