"""Avaliação humana da resposta de cada agente.

Dá a taxa de aprovação humana por área, por nível de confiança e por veredito do
Quality Gate. Uma resposta aprovada pelo Quality Gate e marcada como não útil é um
erro que as regras deixaram passar. É a percepção de quem usou, não uma acurácia
contra gabarito.
"""

from fastapi import HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    AgentResponseFeedback,
    AgentSkill,
    AgentSkillInvocation,
    ConsolidatedResponse,
    TechnicalRequest,
)
from app.schemas.orchestration import AgentResponseFeedbackWrite
from app.services.audit_service import record_audit


def _completed_invocation(
    db: Session, technical_request: TechnicalRequest, invocation_id: str
) -> AgentSkillInvocation:
    invocation = db.scalar(
        select(AgentSkillInvocation).where(
            AgentSkillInvocation.id == invocation_id,
            AgentSkillInvocation.technical_request_id == technical_request.id,
            AgentSkillInvocation.status == "COMPLETED",
        )
    )
    if invocation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Resposta do agente não encontrada."
        )
    return invocation


def save_feedback(
    db: Session,
    request: Request,
    *,
    technical_request: TechnicalRequest,
    invocation_id: str,
    user_id: str,
    data: AgentResponseFeedbackWrite,
) -> AgentResponseFeedback:
    invocation = _completed_invocation(db, technical_request, invocation_id)
    feedback = db.scalar(
        select(AgentResponseFeedback).where(AgentResponseFeedback.invocation_id == invocation.id)
    )
    if feedback is None:
        feedback = AgentResponseFeedback(invocation_id=invocation.id, user_id=user_id, useful=data.useful)
        db.add(feedback)
    feedback.user_id = user_id
    feedback.useful = data.useful
    feedback.reason = data.reason
    feedback.comment = data.comment
    # O comentário fica fora da auditoria: pode trazer dados do caso.
    record_audit(
        db,
        request,
        "AGENT_RESPONSE_RATED",
        user_id=user_id,
        details={
            "trace_id": technical_request.trace_id,
            "invocation_id": invocation.id,
            "useful": data.useful,
            "reason": data.reason,
        },
    )
    db.commit()
    db.refresh(feedback)
    return feedback


def remove_feedback(
    db: Session, request: Request, *, technical_request: TechnicalRequest, invocation_id: str, user_id: str
) -> None:
    invocation = _completed_invocation(db, technical_request, invocation_id)
    feedback = db.scalar(
        select(AgentResponseFeedback).where(AgentResponseFeedback.invocation_id == invocation.id)
    )
    if feedback is None:
        return
    db.delete(feedback)
    record_audit(
        db,
        request,
        "AGENT_RESPONSE_RATING_REMOVED",
        user_id=user_id,
        details={"trace_id": technical_request.trace_id, "invocation_id": invocation.id},
    )
    db.commit()


def feedback_by_invocation(db: Session, invocation_ids: list[str]) -> dict[str, AgentResponseFeedback]:
    if not invocation_ids:
        return {}
    rows = db.scalars(
        select(AgentResponseFeedback).where(AgentResponseFeedback.invocation_id.in_(invocation_ids))
    )
    return {feedback.invocation_id: feedback for feedback in rows}


def feedback_counts(db: Session) -> list[tuple[str, str, str, str, int]]:
    """(área, confiança, veredito do Quality Gate, útil, quantidade) para as métricas."""
    rows = db.execute(
        select(
            AgentSkill.domain,
            AgentSkillInvocation.confidence_level,
            ConsolidatedResponse.quality_gate_approved,
            AgentResponseFeedback.useful,
            func.count(),
        )
        .join(AgentSkillInvocation, AgentResponseFeedback.invocation_id == AgentSkillInvocation.id)
        .join(AgentSkill, AgentSkillInvocation.agent_skill_id == AgentSkill.id)
        .outerjoin(
            ConsolidatedResponse,
            ConsolidatedResponse.technical_request_id == AgentSkillInvocation.technical_request_id,
        )
        .group_by(
            AgentSkill.domain,
            AgentSkillInvocation.confidence_level,
            ConsolidatedResponse.quality_gate_approved,
            AgentResponseFeedback.useful,
        )
    ).all()
    gate = {True: "approved", False: "human_review", None: "none"}
    return [
        (domain, confidence or "NONE", gate[approved], "true" if useful else "false", count)
        for domain, confidence, approved, useful, count in rows
    ]
