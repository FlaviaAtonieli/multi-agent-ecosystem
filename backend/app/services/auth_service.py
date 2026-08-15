from datetime import timedelta

from fastapi import HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    email_fingerprint,
    ensure_utc,
    normalize_email,
    perform_dummy_password_check,
    utc_now,
    verify_password,
)
from app.models import User
from app.services.audit_service import record_audit


def authenticate_user(db: Session, request: Request, email: str, password: str) -> User:
    normalized_email = normalize_email(email)
    user = db.scalar(select(User).where(User.email == normalized_email))

    if user is None:
        perform_dummy_password_check(password)
        record_audit(
            db,
            request,
            "AUTH_LOGIN_FAILED",
            details={"email_fingerprint": email_fingerprint(normalized_email)},
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha inválidos.",
        )

    now = utc_now()
    locked_until = ensure_utc(user.locked_until)
    if locked_until and locked_until > now:
        record_audit(db, request, "AUTH_LOGIN_BLOCKED", user_id=user.id)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Conta temporariamente bloqueada. Tente novamente mais tarde.",
        )

    if not verify_password(password, user.password_hash):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= settings.login_max_attempts:
            user.locked_until = now + timedelta(minutes=settings.lockout_minutes)
            user.failed_login_attempts = 0
        record_audit(db, request, "AUTH_LOGIN_FAILED", user_id=user.id)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha inválidos.",
        )

    if not user.is_active:
        record_audit(db, request, "AUTH_LOGIN_INACTIVE_USER", user_id=user.id)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta conta está desativada.",
        )

    user.failed_login_attempts = 0
    user.locked_until = None
    return user
