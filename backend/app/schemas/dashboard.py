from datetime import datetime

from pydantic import BaseModel


class SecurityEventRead(BaseModel):
    event_type: str
    created_at: datetime


class DashboardSummary(BaseModel):
    active_sessions: int
    registered_agent_skills: int = 0
    orchestration_executions: int = 0
    recent_security_events: list[SecurityEventRead]
    total_users: int | None = None
