from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_session
from app.core.database import get_db
from app.core.security import ensure_utc, utc_now
from app.models import (
    AgentSkill,
    AuditLog,
    AuthSession,
    OrchestrationEvent,
    OrchestrationRun,
    TechnicalRequest,
    User,
)
from app.schemas.dashboard import DashboardSummary, SecurityEventRead
from app.schemas.orchestration import OrchestrationEventRead, TechnicalRequestRead
from app.services.orchestration_service import ACTIVE_STATUSES, RequestStatus


router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def dashboard_summary(
    db: Session = Depends(get_db),
    current_session: AuthSession = Depends(get_current_session),
) -> DashboardSummary:
    owner_id = current_session.user_id
    active_sessions = db.scalar(
        select(func.count(AuthSession.id)).where(
            AuthSession.user_id == owner_id,
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > utc_now(),
        )
    ) or 0

    recent_security_events = list(
        db.scalars(
            select(AuditLog)
            .where(AuditLog.user_id == owner_id)
            .order_by(AuditLog.created_at.desc())
            .limit(6)
        )
    )

    orchestration_executions = db.scalar(
        select(func.count(TechnicalRequest.id)).where(TechnicalRequest.owner_id == owner_id)
    ) or 0

    running_orchestrations = db.scalar(
        select(func.count(TechnicalRequest.id)).where(
            TechnicalRequest.owner_id == owner_id,
            TechnicalRequest.status.in_(ACTIVE_STATUSES),
        )
    ) or 0

    awaiting_context = db.scalar(
        select(func.count(TechnicalRequest.id)).where(
            TechnicalRequest.owner_id == owner_id,
            TechnicalRequest.status == RequestStatus.AWAITING_CONTEXT,
        )
    ) or 0

    start_of_today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    completed_today = db.scalar(
        select(func.count(TechnicalRequest.id)).where(
            TechnicalRequest.owner_id == owner_id,
            TechnicalRequest.status == RequestStatus.COMPLETED,
            TechnicalRequest.updated_at >= start_of_today,
        )
    ) or 0

    completed_count = db.scalar(
        select(func.count(TechnicalRequest.id)).where(
            TechnicalRequest.owner_id == owner_id,
            TechnicalRequest.status == RequestStatus.COMPLETED,
        )
    ) or 0
    failed_count = db.scalar(
        select(func.count(TechnicalRequest.id)).where(
            TechnicalRequest.owner_id == owner_id,
            TechnicalRequest.status == RequestStatus.FAILED,
        )
    ) or 0
    finished_count = completed_count + failed_count
    success_rate = round(completed_count / finished_count, 4) if finished_count else 0.0

    completed_runs = list(
        db.scalars(
            select(OrchestrationRun)
            .join(TechnicalRequest)
            .where(
                TechnicalRequest.owner_id == owner_id,
                OrchestrationRun.started_at.is_not(None),
                OrchestrationRun.completed_at.is_not(None),
            )
        )
    )
    durations = []
    for run in completed_runs:
        started_at = ensure_utc(run.started_at)
        completed_at = ensure_utc(run.completed_at)
        if started_at and completed_at:
            durations.append((completed_at - started_at).total_seconds())
    average_duration_seconds = round(sum(durations) / len(durations), 2) if durations else 0.0

    recent_requests = list(
        db.scalars(
            select(TechnicalRequest)
            .where(TechnicalRequest.owner_id == owner_id)
            .order_by(TechnicalRequest.created_at.desc())
            .limit(6)
        )
    )

    recent_orchestration_events = list(
        db.scalars(
            select(OrchestrationEvent)
            .join(TechnicalRequest)
            .where(TechnicalRequest.owner_id == owner_id)
            .order_by(OrchestrationEvent.created_at.desc(), OrchestrationEvent.sequence_number.desc())
            .limit(8)
        )
    )

    total_users = None
    if current_session.user.role == "ADMIN":
        total_users = db.scalar(select(func.count(User.id))) or 0

    registered_agent_skills = db.scalar(
        select(func.count(AgentSkill.id)).where(
            AgentSkill.status == "approved",
            AgentSkill.enabled.is_(True),
        )
    ) or 0

    return DashboardSummary(
        active_sessions=active_sessions,
        registered_agent_skills=registered_agent_skills,
        orchestration_executions=orchestration_executions,
        running_orchestrations=running_orchestrations,
        awaiting_context=awaiting_context,
        completed_today=completed_today,
        success_rate=success_rate,
        average_duration_seconds=average_duration_seconds,
        recent_security_events=[
            SecurityEventRead(event_type=event.event_type, created_at=event.created_at)
            for event in recent_security_events
        ],
        recent_requests=[TechnicalRequestRead.model_validate(item) for item in recent_requests],
        recent_orchestration_events=[
            OrchestrationEventRead.model_validate(item) for item in recent_orchestration_events
        ],
        total_users=total_users,
    )
