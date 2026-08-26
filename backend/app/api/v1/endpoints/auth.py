from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_current_session,
    get_current_user,
    require_authenticated_csrf,
    require_public_csrf,
)
from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import login_rate_limit, register_rate_limit, renew_rate_limit
from app.core.security import generate_csrf_token, hash_password, normalize_email, utc_now
from app.models import AuthSession, User
from app.schemas.auth import AuthResponse, CsrfResponse, LoginRequest, SessionRead
from app.schemas.user import UserCreate, UserRead
from app.services.audit_service import record_audit
from app.services.auth_service import authenticate_user
from app.services.session_service import (
    clear_auth_cookies,
    create_session,
    revoke_all_sessions,
    revoke_session,
    rotate_session,
    set_auth_cookies,
    set_public_csrf_cookie,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/csrf", response_model=CsrfResponse)
def prepare_csrf(response: Response) -> CsrfResponse:
    set_public_csrf_cookie(response, generate_csrf_token())
    return CsrfResponse()


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(
    request: Request,
    response: Response,
    payload: UserCreate,
    db: Session = Depends(get_db),
    _csrf: None = Depends(require_public_csrf),
    _rate: None = Depends(register_rate_limit),
) -> AuthResponse:
    if not settings.allow_registration:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Novos cadastros estão desativados."
        )

    email = normalize_email(str(payload.email))
    existing = db.scalar(select(User).where(User.email == email))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Não foi possível criar a conta com os dados informados.",
        )

    user = User(
        name=payload.name,
        email=email,
        password_hash=hash_password(payload.password),
        role="USER",
        is_active=True,
    )
    db.add(user)
    db.flush()

    auth_session, raw_token, csrf_token = create_session(db, user, request)
    record_audit(db, request, "AUTH_REGISTER_SUCCESS", user_id=user.id)
    db.commit()
    db.refresh(user)
    db.refresh(auth_session)

    set_auth_cookies(response, raw_token, csrf_token)
    return AuthResponse(user=UserRead.model_validate(user), session_expires_at=auth_session.expires_at)


@router.post("/login", response_model=AuthResponse)
def login(
    request: Request,
    response: Response,
    payload: LoginRequest,
    db: Session = Depends(get_db),
    _csrf: None = Depends(require_public_csrf),
    _rate: None = Depends(login_rate_limit),
) -> AuthResponse:
    user = authenticate_user(db, request, str(payload.email), payload.password)
    auth_session, raw_token, csrf_token = create_session(db, user, request)
    record_audit(db, request, "AUTH_LOGIN_SUCCESS", user_id=user.id, details={"session_id": auth_session.id})
    db.commit()
    db.refresh(user)
    db.refresh(auth_session)

    set_auth_cookies(response, raw_token, csrf_token)
    return AuthResponse(user=UserRead.model_validate(user), session_expires_at=auth_session.expires_at)


@router.post("/renew", response_model=AuthResponse)
def renew_session(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    current_session: AuthSession = Depends(require_authenticated_csrf),
    _rate: None = Depends(renew_rate_limit),
) -> AuthResponse:
    user = current_session.user
    renewed_session, raw_token, csrf_token = rotate_session(db, current_session, user, request)
    record_audit(
        db,
        request,
        "AUTH_SESSION_RENEWED",
        user_id=user.id,
        details={"previous_session_id": current_session.id, "session_id": renewed_session.id},
    )
    db.commit()
    db.refresh(renewed_session)
    set_auth_cookies(response, raw_token, csrf_token)
    return AuthResponse(user=UserRead.model_validate(user), session_expires_at=renewed_session.expires_at)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    current_session: AuthSession = Depends(require_authenticated_csrf),
) -> Response:
    revoke_session(current_session)
    record_audit(
        db,
        request,
        "AUTH_LOGOUT",
        user_id=current_session.user_id,
        details={"session_id": current_session.id},
    )
    db.commit()
    clear_auth_cookies(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
def logout_all(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    current_session: AuthSession = Depends(require_authenticated_csrf),
) -> Response:
    revoked_count = revoke_all_sessions(db, current_session.user_id)
    record_audit(
        db,
        request,
        "AUTH_LOGOUT_ALL",
        user_id=current_session.user_id,
        details={"revoked_sessions": revoked_count},
    )
    db.commit()
    clear_auth_cookies(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(get_current_user)) -> UserRead:
    return UserRead.model_validate(user)


@router.get("/sessions", response_model=list[SessionRead])
def list_sessions(
    db: Session = Depends(get_db),
    current_session: AuthSession = Depends(get_current_session),
) -> list[SessionRead]:
    rows = list(
        db.scalars(
            select(AuthSession)
            .where(
                AuthSession.user_id == current_session.user_id,
                AuthSession.revoked_at.is_(None),
                AuthSession.expires_at > utc_now(),
            )
            .order_by(AuthSession.created_at.desc())
        )
    )
    return [
        SessionRead(
            id=row.id,
            ip_address=row.ip_address,
            user_agent=row.user_agent,
            expires_at=row.expires_at,
            last_seen_at=row.last_seen_at,
            created_at=row.created_at,
            current=row.id == current_session.id,
        )
        for row in rows
    ]


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_own_session(
    session_id: str,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    current_session: AuthSession = Depends(require_authenticated_csrf),
) -> Response:
    target = db.scalar(
        select(AuthSession).where(
            AuthSession.id == session_id,
            AuthSession.user_id == current_session.user_id,
            AuthSession.revoked_at.is_(None),
        )
    )
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sessão não encontrada.")

    revoke_session(target)
    record_audit(
        db,
        request,
        "AUTH_SESSION_REVOKED",
        user_id=current_session.user_id,
        details={"session_id": target.id},
    )
    db.commit()
    if target.id == current_session.id:
        clear_auth_cookies(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response
