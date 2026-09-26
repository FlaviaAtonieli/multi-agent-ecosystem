from datetime import datetime

from pydantic import BaseModel

from app.schemas.orchestration import OrchestrationEventRead, TechnicalRequestRead


class SecurityEventRead(BaseModel):
    event_type: str
    created_at: datetime


class DashboardSummary(BaseModel):
    active_sessions: int
    registered_agent_skills: int = 0
    orchestration_executions: int = 0
    running_orchestrations: int = 0
    awaiting_context: int = 0
    completed_today: int = 0
    success_rate: float = 0
    average_duration_seconds: float = 0
    recent_security_events: list[SecurityEventRead]
    recent_requests: list[TechnicalRequestRead]
    recent_orchestration_events: list[OrchestrationEventRead]
    total_users: int | None = None
