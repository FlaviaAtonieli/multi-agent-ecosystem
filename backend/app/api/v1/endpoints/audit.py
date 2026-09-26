from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.orm import Session

from app.api.dependencies import require_admin
from app.core.database import get_db
from app.models import OrchestrationEvent, TechnicalRequest, User
from app.schemas.audit import AuditEventPage, AuditEventRead, AuditStats

router = APIRouter(prefix="/audit", tags=["Audit"])

_AUTOMATED_ACTORS = {
    "INTERACTION_GUIDE",
    "ORCHESTRATOR",
    "ADVISORY_AGENT",
    "RETRIEVAL_AGENT",
    "TECHNICAL_PLANNER",
}
_MANUAL_ACTORS = {"USER", "REVIEWER"}
_COMPLIANCE_EVENT_TYPES = {
    "LLM_INVOCATION_FAILED",
    "AGENT_SKILL_INVOCATION_FAILED",
    "HUMAN_REVIEW_REJECTED",
}


@router.get("/events", response_model=AuditEventPage)
def list_audit_events(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
    days: int = Query(7, ge=1, le=90),
    actor: str | None = Query(None),
    search: str | None = Query(None, max_length=160),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> AuditEventPage:
    # Admin-only: the audit trail spans every user's requests, so it stays
    # restricted to the role whose job is system-wide oversight rather than
    # scoped per-owner (see CHANGELOG for the 2026-09-14 owner-scoped
    # experiment this reverts).
    start_of_today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)

    def _count_today(*conditions: ColumnElement[bool]) -> int:
        query = select(func.count(OrchestrationEvent.id)).where(
            OrchestrationEvent.created_at >= start_of_today, *conditions
        )
        return db.scalar(query) or 0

    events_today = _count_today()
    automated_decisions_today = _count_today(OrchestrationEvent.actor.in_(_AUTOMATED_ACTORS))
    manual_interventions_today = _count_today(OrchestrationEvent.actor.in_(_MANUAL_ACTORS))
    compliance_alerts_today = _count_today(OrchestrationEvent.event_type.in_(_COMPLIANCE_EVENT_TYPES))

    since = datetime.now(UTC) - timedelta(days=days)
    query = (
        select(OrchestrationEvent, TechnicalRequest)
        .join(TechnicalRequest, OrchestrationEvent.technical_request_id == TechnicalRequest.id)
        .where(OrchestrationEvent.created_at >= since)
    )
    if actor:
        query = query.where(OrchestrationEvent.actor == actor)
    if search:
        like = f"%{search}%"
        query = query.where(
            or_(TechnicalRequest.title.ilike(like), TechnicalRequest.trace_id.ilike(like))
        )

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0

    rows = db.execute(
        query.order_by(
            OrchestrationEvent.created_at.desc(), OrchestrationEvent.sequence_number.desc()
        )
        .limit(limit)
        .offset(offset)
    ).all()

    items = [
        AuditEventRead(
            id=event.id,
            event_type=event.event_type,
            actor=event.actor,
            title=event.title,
            message=event.message,
            created_at=event.created_at,
            request_id=request.id,
            request_title=request.title,
            request_trace_id=request.trace_id,
        )
        for event, request in rows
    ]

    return AuditEventPage(
        stats=AuditStats(
            events_today=events_today,
            automated_decisions_today=automated_decisions_today,
            manual_interventions_today=manual_interventions_today,
            compliance_alerts_today=compliance_alerts_today,
        ),
        items=items,
        total=total,
    )
