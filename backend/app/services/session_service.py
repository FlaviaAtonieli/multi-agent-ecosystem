from datetime import timedelta

from fastapi import Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import generate_csrf_token, generate_session_token, hash_token, utc_now
from app.models import AuthSession, User
from app.services.audit_service import get_request_ip, get_user_agent


def set_public_csrf_cookie(response: Response, csrf_token: str) -> None:
    response.set_cookie(
        key=settings.csrf_cookie_name,
        value=csrf_token,
        max_age=60 * 60,
        path="/",
        secure=settings.cookie_secure,
        httponly=False,
        samesite="lax",
    )


def set_auth_cookies(response: Response, session_token: str, csrf_token: str) -> None:
    max_age = settings.session_ttl_hours * 60 * 60
    response.set_cookie(
        key=settings.session_cookie_name,
        value=session_token,
        max_age=max_age,
        path="/",
        secure=settings.cookie_secure,
        httponly=True,
        samesite="lax",
    )
    response.set_cookie(
        key=settings.csrf_cookie_name,
        value=csrf_token,
        max_age=max_age,
        path="/",
        secure=settings.cookie_secure,
        httponly=False,
        samesite="lax",
    )


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(
        settings.session_cookie_name,
        path="/",
        secure=settings.cookie_secure,
        httponly=True,
        samesite="lax",
    )
    response.delete_cookie(
        settings.csrf_cookie_name,
        path="/",
        secure=settings.cookie_secure,
        httponly=False,
        samesite="lax",
    )


def create_session(db: Session, user: User, request: Request) -> tuple[AuthSession, str, str]:
    now = utc_now()
    active_sessions = list(
        db.scalars(
            select(AuthSession)
            .where(
                AuthSession.user_id == user.id,
                AuthSession.revoked_at.is_(None),
                AuthSession.expires_at > now,
            )
            .order_by(AuthSession.created_at.asc())
        )
    )

    sessions_to_revoke = max(0, len(active_sessions) - settings.max_active_sessions + 1)
    for old_session in active_sessions[:sessions_to_revoke]:
        old_session.revoked_at = now

    raw_token = generate_session_token()
    csrf_token = generate_csrf_token()
    auth_session = AuthSession(
        user_id=user.id,
        token_hash=hash_token(raw_token),
        csrf_hash=hash_token(csrf_token),
        ip_address=get_request_ip(request),
        user_agent=get_user_agent(request),
        expires_at=now + timedelta(hours=settings.session_ttl_hours),
        last_seen_at=now,
    )
    db.add(auth_session)
    db.flush()
    return auth_session, raw_token, csrf_token


def find_valid_session(db: Session, raw_token: str | None) -> AuthSession | None:
    if not raw_token:
        return None
    now = utc_now()
    return db.scalar(
        select(AuthSession).where(
            AuthSession.token_hash == hash_token(raw_token),
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > now,
        )
    )


def revoke_session(auth_session: AuthSession) -> None:
    if auth_session.revoked_at is None:
        auth_session.revoked_at = utc_now()


def revoke_all_sessions(db: Session, user_id: str) -> int:
    now = utc_now()
    active_sessions = list(
        db.scalars(
            select(AuthSession).where(
                AuthSession.user_id == user_id,
                AuthSession.revoked_at.is_(None),
                AuthSession.expires_at > now,
            )
        )
    )
    for auth_session in active_sessions:
        auth_session.revoked_at = now
    return len(active_sessions)


def rotate_session(
    db: Session,
    current_session: AuthSession,
    user: User,
    request: Request,
) -> tuple[AuthSession, str, str]:
    revoke_session(current_session)
    return create_session(db, user, request)
