"""Execução da orquestração em segundo plano: iniciar, interromper e recuperar depois de um reinício."""

import asyncio
import logging
from collections.abc import Coroutine
from typing import Any, cast

from sqlalchemy import CursorResult, select, update
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import utc_now
from app.models import (
    AgentSkillInvocation,
    TechnicalRequest,
    User,
)
from app.services.agent_skill_orchestration_service import (
    execute_orchestration_step,
    resolve_target_skills,
)
from app.services.orchestration_service import RequestStatus, append_event

logger = logging.getLogger(__name__)

# O asyncio guarda só uma referência fraca às tarefas: sem este conjunto, uma
# execução em segundo plano poderia ser coletada no meio.
_background_tasks: set[asyncio.Task[None]] = set()
# Execução em andamento de cada solicitação, para poder interrompê-la.
_running_orchestrations: dict[str, asyncio.Task[None]] = {}


def has_target_skills(db: Session, technical_request: TechnicalRequest) -> bool:
    return bool(resolve_target_skills(db, technical_request))


def claim_request_for_execution(db: Session, technical_request: TechnicalRequest) -> bool:
    """Passa a solicitação para RUNNING de forma atômica, para dois cliques em "Executar"
    não abrirem duas execuções. FAILED é aceito, para uma execução interrompida poder
    ser repetida.
    """
    claimed = cast(
        CursorResult,
        db.execute(
            update(TechnicalRequest)
            .where(
                TechnicalRequest.id == technical_request.id,
                TechnicalRequest.status.in_(
                    [RequestStatus.QUALIFIED, RequestStatus.FAILED, RequestStatus.CANCELLED]
                ),
            )
            .values(status=RequestStatus.RUNNING)
        ),
    )
    if claimed.rowcount != 1:
        db.rollback()
        return False
    db.refresh(technical_request)
    run = technical_request.orchestration_run
    if run:
        run.status = RequestStatus.RUNNING
        run.completed_at = None
    db.commit()
    return True


def _mark_failed(db: Session, technical_request: TechnicalRequest, *, title: str, message: str) -> None:
    technical_request.status = RequestStatus.FAILED
    run = technical_request.orchestration_run
    if run:
        run.status = RequestStatus.FAILED
        run.completed_at = utc_now()
    append_event(
        db,
        technical_request,
        event_type="ORCHESTRATION_EXECUTION_FAILED",
        actor="ORCHESTRATOR",
        title=title,
        message=message,
    )
    db.commit()


async def _run_orchestration(request_id: str, user_id: str, requested_model: str | None) -> None:
    with SessionLocal() as db:
        technical_request = db.get(TechnicalRequest, request_id)
        user = db.get(User, user_id)
        if technical_request is None or user is None:
            logger.error("Orquestração %s não iniciada: solicitação ou usuário não encontrado.", request_id)
            return
        try:
            await execute_orchestration_step(
                db, technical_request=technical_request, user=user, requested_model=requested_model
            )
        except asyncio.CancelledError:
            db.rollback()
            _mark_cancelled(db, technical_request)
            raise
        except Exception:  # noqa: BLE001 - ninguém espera a resposta: o erro fica registrado na solicitação
            logger.exception("Falha na orquestração em segundo plano %s", technical_request.trace_id)
            db.rollback()
            _mark_failed(
                db,
                technical_request,
                title="Falha na execução da orquestração",
                message="A execução foi interrompida por um erro inesperado. Tente executar novamente.",
            )


def spawn(coroutine: Coroutine[Any, Any, None]) -> asyncio.Task[None]:
    task = asyncio.create_task(coroutine)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return task


def _mark_cancelled(db: Session, technical_request: TechnicalRequest) -> None:
    db.execute(
        update(AgentSkillInvocation)
        .where(
            AgentSkillInvocation.technical_request_id == technical_request.id,
            AgentSkillInvocation.status == "STARTED",
        )
        .values(status="CANCELLED", completed_at=utc_now())
    )
    technical_request.status = RequestStatus.CANCELLED
    run = technical_request.orchestration_run
    if run:
        run.status = RequestStatus.CANCELLED
        run.completed_at = utc_now()
    append_event(
        db,
        technical_request,
        event_type="ORCHESTRATION_CANCELLED",
        actor="USER",
        title="Execução interrompida",
        message="A pessoa interrompeu a execução. Dá para complementar o contexto e executar de novo.",
    )
    db.commit()


def cancel_orchestration(db: Session, technical_request: TechnicalRequest) -> bool:
    """Interrompe a execução em andamento. A tarefa marca a solicitação como
    CANCELLED ao parar. Sem tarefa neste processo (o servidor reiniciou), marca na hora."""
    if technical_request.status != RequestStatus.RUNNING:
        return False
    task = _running_orchestrations.get(technical_request.id)
    if task is not None and not task.done():
        task.cancel()
    else:
        _mark_cancelled(db, technical_request)
    return True


def start_orchestration_in_background(
    *, request_id: str, user_id: str, requested_model: str | None = None
) -> None:
    """Roda a orquestração fora da requisição HTTP: as skills somam minutos, mais que os
    45 s que o proxy do Static Web Apps espera. A tela acompanha pela linha do tempo.
    """
    task = spawn(_run_orchestration(request_id, user_id, requested_model))
    _running_orchestrations[request_id] = task
    task.add_done_callback(lambda _: _running_orchestrations.pop(request_id, None))


def fail_interrupted_orchestrations(db: Session) -> int:
    """Chamado na subida. A execução em segundo plano vive só neste processo, então uma
    solicitação ainda RUNNING depois de reiniciar nunca termina. Supõe um processo só
    (ver o CMD do backend/Dockerfile); com vários, falharia execuções vivas em outro.
    """
    interrupted = list(
        db.scalars(select(TechnicalRequest).where(TechnicalRequest.status == RequestStatus.RUNNING))
    )
    for technical_request in interrupted:
        _mark_failed(
            db,
            technical_request,
            title="Execução interrompida",
            message="O servidor reiniciou durante a execução. Tente executar novamente.",
        )
    return len(interrupted)
