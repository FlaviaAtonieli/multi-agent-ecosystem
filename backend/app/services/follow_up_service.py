"""Perguntas de acompanhamento sobre uma resposta já entregue, respondidas pelas mesmas skills."""

import json
import logging

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agent_catalog.registry import canonical_domain
from app.core.database import SessionLocal
from app.llm.file_request import asks_for_files
from app.models import (
    AgentSkill,
    FollowUpExchange,
    OrchestrationEvent,
    TechnicalRequest,
    User,
)
from app.quality_gate.service import evaluate
from app.services.agent_skill_orchestration_service import (
    NoAgentSkillsAvailableError,
    active_clan_skills,
    build_technical_synthesis,
    invoke_skills,
    overall_confidence,
    resolve_target_skills,
    stored_any_file,
)
from app.services.orchestration_runner import spawn
from app.services.orchestration_service import append_event

logger = logging.getLogger(__name__)

_FOLLOW_UP_EVENT_TYPES = ("FOLLOW_UP_QUESTION_ASKED", "FOLLOW_UP_RESPONSE_RECEIVED", "FOLLOW_UP_FAILED")
_NO_FOLLOW_UP_SKILLS_MESSAGE = "Nenhuma Agent Skill ativa disponível para responder a esta pergunta."


async def ask_follow_up_question(
    db: Session,
    *,
    technical_request: TechnicalRequest,
    user: User,
    question: str,
    target_domain: str | None = None,
    requested_model: str | None = None,
) -> FollowUpExchange:
    """Continues the same orchestration chain (trace_id) after the initial
    execution: the user can keep asking questions, either broadcast to every
    domain the original run used (target_domain=None) or aimed at one
    specific Agent Skill domain. Every round — even a single agent answering —
    still goes through the same Quality Gate as the initial execution (RF11),
    and is kept as its own row so the conversation history survives (unlike
    ConsolidatedResponse, one per TechnicalRequest)."""
    skills = _follow_up_skills(db, technical_request, target_domain)
    if not skills:
        raise NoAgentSkillsAvailableError(_NO_FOLLOW_UP_SKILLS_MESSAGE)

    record_follow_up_question(db, technical_request, question=question, target_domain=target_domain)
    return await _answer_follow_up(
        db,
        technical_request=technical_request,
        user=user,
        skills=skills,
        question=question,
        target_domain=target_domain,
        requested_model=requested_model,
    )


def _follow_up_skills(
    db: Session, technical_request: TechnicalRequest, target_domain: str | None
) -> list[AgentSkill]:
    if target_domain:
        canonical = canonical_domain(db, target_domain)
        return [skill for skill in active_clan_skills(db, technical_request) if skill.domain == canonical]
    return resolve_target_skills(db, technical_request)


def has_follow_up_skills(
    db: Session, technical_request: TechnicalRequest, target_domain: str | None
) -> bool:
    return bool(_follow_up_skills(db, technical_request, target_domain))


def record_follow_up_question(
    db: Session, technical_request: TechnicalRequest, *, question: str, target_domain: str | None
) -> None:
    append_event(
        db,
        technical_request,
        event_type="FOLLOW_UP_QUESTION_ASKED",
        actor="USER",
        title="Pergunta de acompanhamento registrada",
        message=question,
        payload={"target_domain": target_domain},
    )
    db.commit()


def has_pending_follow_up(db: Session, technical_request: TechnicalRequest) -> bool:
    """The timeline is the source of truth: a question is pending while it is the
    latest follow-up event of the request."""
    latest = db.scalar(
        select(OrchestrationEvent.event_type)
        .where(
            OrchestrationEvent.technical_request_id == technical_request.id,
            OrchestrationEvent.event_type.in_(_FOLLOW_UP_EVENT_TYPES),
        )
        .order_by(OrchestrationEvent.sequence_number.desc())
        .limit(1)
    )
    return latest == "FOLLOW_UP_QUESTION_ASKED"


async def _run_follow_up(
    request_id: str,
    user_id: str,
    question: str,
    target_domain: str | None,
    requested_model: str | None,
) -> None:
    with SessionLocal() as db:
        technical_request = db.get(TechnicalRequest, request_id)
        user = db.get(User, user_id)
        if technical_request is None or user is None:
            logger.error("Pergunta da solicitação %s não respondida: registro não encontrado.", request_id)
            return
        try:
            skills = _follow_up_skills(db, technical_request, target_domain)
            if not skills:
                raise NoAgentSkillsAvailableError(_NO_FOLLOW_UP_SKILLS_MESSAGE)
            await _answer_follow_up(
                db,
                technical_request=technical_request,
                user=user,
                skills=skills,
                question=question,
                target_domain=target_domain,
                requested_model=requested_model,
            )
        except Exception:  # noqa: BLE001 - no caller left to answer: record it on the request instead
            logger.exception("Falha na pergunta em segundo plano %s", technical_request.trace_id)
            db.rollback()
            _record_follow_up_failure(
                db, technical_request, "A pergunta não pôde ser respondida. Tente novamente."
            )


def start_follow_up_in_background(
    *,
    request_id: str,
    user_id: str,
    question: str,
    target_domain: str | None = None,
    requested_model: str | None = None,
) -> None:
    """Same reason as start_orchestration_in_background: several skills can take
    longer than the 45 s limit of the Static Web Apps proxy."""
    spawn(_run_follow_up(request_id, user_id, question, target_domain, requested_model))


def _record_follow_up_failure(db: Session, technical_request: TechnicalRequest, message: str) -> None:
    append_event(
        db,
        technical_request,
        event_type="FOLLOW_UP_FAILED",
        actor="ORCHESTRATOR",
        title="Falha na pergunta de acompanhamento",
        message=message,
    )
    db.commit()


def fail_interrupted_follow_ups(db: Session) -> int:
    """Same assumption as fail_interrupted_orchestrations: one worker process."""
    request_ids = db.scalars(
        select(OrchestrationEvent.technical_request_id)
        .where(OrchestrationEvent.event_type == "FOLLOW_UP_QUESTION_ASKED")
        .distinct()
    ).all()
    interrupted = 0
    for request_id in request_ids:
        technical_request = db.get(TechnicalRequest, request_id)
        if technical_request is not None and has_pending_follow_up(db, technical_request):
            _record_follow_up_failure(
                db, technical_request, "O servidor reiniciou antes da resposta. Faça a pergunta novamente."
            )
            interrupted += 1
    return interrupted


async def _answer_follow_up(
    db: Session,
    *,
    technical_request: TechnicalRequest,
    user: User,
    skills: list[AgentSkill],
    question: str,
    target_domain: str | None,
    requested_model: str | None,
) -> FollowUpExchange:
    invocations, results = await invoke_skills(
        db,
        skills=skills,
        technical_request=technical_request,
        user=user,
        requested_model=requested_model,
        additional_question=question,
    )

    verdict = evaluate(
        results,
        files_requested=asks_for_files(question),
        files_delivered=stored_any_file(db, invocations),
    )
    append_event(
        db,
        technical_request,
        event_type="QUALITY_GATE_EVALUATED",
        actor="ADVISORY_AGENT",
        title="Quality Gate avaliado (pergunta de acompanhamento)",
        message="; ".join(verdict.reasons) if verdict.reasons else "Avaliação concluída.",
        payload=json.loads(verdict.model_dump_json()),
    )

    next_sequence = (
        db.scalar(
            select(func.coalesce(func.max(FollowUpExchange.sequence_number), 0)).where(
                FollowUpExchange.technical_request_id == technical_request.id
            )
        )
        or 0
    ) + 1

    exchange = FollowUpExchange(
        technical_request_id=technical_request.id,
        trace_id=technical_request.trace_id,
        asked_by_id=user.id,
        sequence_number=next_sequence,
        question=question,
        target_domain=target_domain,
        synthesis=build_technical_synthesis(results),
        results=[result.model_dump(mode="json") for result in results],
        overall_confidence_level=overall_confidence(results),
        quality_gate_approved=verdict.approved,
        requires_human_review=verdict.requires_human_review,
    )
    db.add(exchange)
    append_event(
        db,
        technical_request,
        event_type="FOLLOW_UP_RESPONSE_RECEIVED",
        actor="ORCHESTRATOR",
        title="Resposta de acompanhamento consolidada",
        message=(
            f"{len(results)} resposta(s) recebida(s) para a pergunta de acompanhamento "
            f"(confiança geral: {exchange.overall_confidence_level})."
        ),
        payload={"target_domain": target_domain, "sequence_number": next_sequence},
    )

    db.commit()
    db.refresh(exchange)
    return exchange
