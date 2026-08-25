from datetime import timedelta

from fastapi import Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.roles import HUMAN_REVIEW_ROLES, LLM_EXECUTION_ROLES, ROLE_ADMIN
from app.core.security import ensure_utc, hash_token, secure_compare, utc_now
from app.models import AuthSession, User
from app.services.session_service import clear_auth_cookies, find_valid_session, revoke_session


def require_public_csrf(request: Request) -> None:
    cookie_token = request.cookies.get(settings.csrf_cookie_name)
    header_token = request.headers.get("X-CSRF-Token")
    if not cookie_token or not header_token or not secure_compare(cookie_token, header_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Validação CSRF inválida. Atualize a página e tente novamente.",
        )


def get_current_session(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> AuthSession:
    raw_token = request.cookies.get(settings.session_cookie_name)
    auth_session = find_valid_session(db, raw_token)
    if auth_session is None:
        clear_auth_cookies(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessão ausente ou expirada.",
        )

    user = auth_session.user
    if not user or not user.is_active:
        revoke_session(auth_session)
        db.commit()
        clear_auth_cookies(response)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta conta não possui acesso ao sistema.",
        )

    last_seen = ensure_utc(auth_session.last_seen_at)
    now = utc_now()
    if last_seen is None or now - last_seen > timedelta(minutes=5):
        auth_session.last_seen_at = now
        db.commit()

    return auth_session


def require_authenticated_csrf(
    request: Request,
    auth_session: AuthSession = Depends(get_current_session),
) -> AuthSession:
    require_public_csrf(request)
    cookie_token = request.cookies.get(settings.csrf_cookie_name)
    if cookie_token is None or not secure_compare(hash_token(cookie_token), auth_session.csrf_hash):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="O token CSRF não pertence à sessão atual.",
        )
    return auth_session


def get_current_user(auth_session: AuthSession = Depends(get_current_session)) -> User:
    return auth_session.user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != ROLE_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ação permitida apenas para administradores.",
        )
    return user


def require_technician(user: User = Depends(get_current_user)) -> User:
    if user.role not in LLM_EXECUTION_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ação permitida apenas para técnicos autorizados.",
        )
    return user


def require_reviewer(user: User = Depends(get_current_user)) -> User:
    if user.role not in HUMAN_REVIEW_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ação permitida apenas para revisores ou administradores.",
        )
    return user
