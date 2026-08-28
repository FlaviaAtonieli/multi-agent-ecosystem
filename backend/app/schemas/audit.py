from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuditEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    event_type: str
    actor: str
    title: str
    message: str
    created_at: datetime
    request_id: str
    request_title: str
    request_trace_id: str


class AuditStats(BaseModel):
    events_today: int
    automated_decisions_today: int
    manual_interventions_today: int
    compliance_alerts_today: int


class AuditEventPage(BaseModel):
    stats: AuditStats
    items: list[AuditEventRead]
    total: int
