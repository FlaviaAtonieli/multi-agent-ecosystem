from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_session
from app.core.database import get_db
from app.core.security import utc_now
from app.models import AuditLog, AuthSession, User
from app.schemas.dashboard import DashboardSummary, SecurityEventRead


router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def dashboard_summary(
    db: Session = Depends(get_db),
    current_session: AuthSession = Depends(get_current_session),
) -> DashboardSummary:
    active_sessions = db.scalar(
        select(func.count(AuthSession.id)).where(
            AuthSession.user_id == current_session.user_id,
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > utc_now(),
        )
    ) or 0

    recent_events = list(
        db.scalars(
            select(AuditLog)
            .where(AuditLog.user_id == current_session.user_id)
            .order_by(AuditLog.created_at.desc())
            .limit(6)
        )
    )

    total_users = None
    if current_session.user.role == "ADMIN":
        total_users = db.scalar(select(func.count(User.id))) or 0

    return DashboardSummary(
        active_sessions=active_sessions,
        registered_agent_skills=0,
        orchestration_executions=0,
        recent_security_events=[
            SecurityEventRead(event_type=event.event_type, created_at=event.created_at) for event in recent_events
        ],
        total_users=total_users,
    )
