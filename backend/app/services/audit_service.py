from fastapi import Request
from sqlalchemy.orm import Session

from app.models import AuditLog


def get_request_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def get_user_agent(request: Request) -> str | None:
    value = request.headers.get("User-Agent")
    return value[:1000] if value else None


def record_audit(
    db: Session,
    request: Request,
    event_type: str,
    *,
    user_id: str | None = None,
    details: dict | None = None,
) -> AuditLog:
    event = AuditLog(
        user_id=user_id,
        event_type=event_type,
        ip_address=get_request_ip(request),
        user_agent=get_user_agent(request),
        details=details or {},
    )
    db.add(event)
    return event
