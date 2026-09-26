from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
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
from app.core.rate_limit import (
    github_oauth_rate_limit,
    login_rate_limit,
    register_rate_limit,
    renew_rate_limit,
)
from app.core.security import (
    generate_csrf_token,
    hash_password,
    normalize_email,
    secure_compare,
    utc_now,
    verify_password,
)
from app.models import AuthSession, User
from app.schemas.auth import AuthResponse, CsrfResponse, LoginRequest, SessionRead
from app.schemas.user import PasswordChange, UserCreate, UserNameUpdate, UserRead
from app.services.audit_service import record_audit
from app.services.auth_service import authenticate_user
from app.services.github_oauth_service import (
    GitHubAccountConflictError,
    GitHubOAuthError,
    build_authorize_url,
    exchange_code_for_access_token,
    fetch_github_profile,
    find_or_create_user,
)
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

GITHUB_OAUTH_STATE_COOKIE = "agenthub_github_oauth_state"


def _to_user_read(user: User) -> UserRead:
    """UserRead.model_validate(user) alone would silently report has_password=False
    for everyone (it isn't a real column, just a default) -- every response that
    serializes a User must go through here instead."""
    data = UserRead.model_validate(user).model_dump()
    data["has_password"] = user.password_hash is not None
    return UserRead(**data)


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
    return AuthResponse(user=_to_user_read(user), session_expires_at=auth_session.expires_at)


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
    return AuthResponse(user=_to_user_read(user), session_expires_at=auth_session.expires_at)


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
    return AuthResponse(user=_to_user_read(user), session_expires_at=renewed_session.expires_at)


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
    return _to_user_read(user)


@router.post("/onboarding/complete", response_model=UserRead)
def complete_onboarding(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _: AuthSession = Depends(require_authenticated_csrf),
) -> UserRead:
    if user.onboarding_completed_at is None:
        user.onboarding_completed_at = utc_now()
        db.commit()
        db.refresh(user)
    return _to_user_read(user)


@router.patch("/me", response_model=UserRead)
def update_my_name(
    payload: UserNameUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _: AuthSession = Depends(require_authenticated_csrf),
) -> UserRead:
    user.name = payload.name
    record_audit(db, request, "ACCOUNT_NAME_UPDATED", user_id=user.id)
    db.commit()
    db.refresh(user)
    return _to_user_read(user)


@router.post("/me/password", response_model=UserRead)
def change_my_password(
    payload: PasswordChange,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _: AuthSession = Depends(require_authenticated_csrf),
) -> UserRead:
    if user.password_hash is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Esta conta usa login com GitHub e não tem senha própria.",
        )
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Senha atual incorreta.")

    user.password_hash = hash_password(payload.new_password)
    record_audit(db, request, "ACCOUNT_PASSWORD_CHANGED", user_id=user.id)
    db.commit()
    db.refresh(user)
    return _to_user_read(user)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_account(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    current_session: AuthSession = Depends(require_authenticated_csrf),
) -> Response:
    """Soft delete: várias outras tabelas referenciam users.id com
    ondelete=RESTRICT (AgentSkill.submitted_by_id, Clan.created_by_id,
    ClanMembership.added_by_id, FollowUpExchange.asked_by_id,
    LLMInvocation.user_id -- essa última criada por toda orquestração já
    executada) -- um DELETE de verdade falharia pra praticamente qualquer
    conta que já usou o sistema. Em vez disso, desativa e limpa nome/e-mail/
    identidade, preservando a linha (e todo o histórico que aponta pra ela)."""
    user.is_active = False
    user.name = "Conta removida"
    user.email = f"conta-removida-{user.id}@removida.local"
    user.avatar_url = None
    user.github_id = None
    user.password_hash = None

    revoked_count = revoke_all_sessions(db, user.id)
    record_audit(
        db, request, "ACCOUNT_SELF_DELETED", user_id=user.id, details={"revoked_sessions": revoked_count}
    )
    db.commit()

    clear_auth_cookies(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


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


def _frontend_redirect(path: str, **query: str) -> RedirectResponse:
    url = f"{settings.frontend_base_url}{path}"
    if query:
        url = f"{url}?{urlencode(query)}"
    return RedirectResponse(url, status_code=status.HTTP_302_FOUND)


def _clear_github_state_cookie(response: Response) -> None:
    response.delete_cookie(GITHUB_OAUTH_STATE_COOKIE, path=f"{settings.api_v1_prefix}/auth/github")


def _require_github_oauth_enabled() -> None:
    if not settings.github_oauth_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Login com GitHub não está habilitado."
        )


@router.get("/github/login")
def github_login(_rate: None = Depends(github_oauth_rate_limit)) -> RedirectResponse:
    """Redirects to GitHub's authorize screen. The `state` value is GitHub
    OAuth's own CSRF protection (distinct from the app's session CSRF token,
    which can't be used here -- this leg of the flow is a plain browser
    navigation, not a fetch call from our own frontend): it's generated here,
    stashed in a short-lived cookie, and checked back on /github/callback."""
    _require_github_oauth_enabled()

    state = generate_csrf_token()
    redirect = RedirectResponse(build_authorize_url(state), status_code=status.HTTP_302_FOUND)
    redirect.set_cookie(
        key=GITHUB_OAUTH_STATE_COOKIE,
        value=state,
        max_age=600,
        path=f"{settings.api_v1_prefix}/auth/github",
        secure=settings.cookie_secure,
        httponly=True,
        samesite="lax",
    )
    return redirect


@router.get("/github/callback")
def github_callback(
    request: Request,
    db: Session = Depends(get_db),
    code: str | None = None,
    state: str | None = None,
    _rate: None = Depends(github_oauth_rate_limit),
) -> RedirectResponse:
    _require_github_oauth_enabled()

    cookie_state = request.cookies.get(GITHUB_OAUTH_STATE_COOKIE)
    if not code or not state or not cookie_state or not secure_compare(state, cookie_state):
        record_audit(db, request, "AUTH_GITHUB_STATE_MISMATCH")
        db.commit()
        redirect = _frontend_redirect("/login", error="github_oauth_failed")
        _clear_github_state_cookie(redirect)
        return redirect

    try:
        access_token = exchange_code_for_access_token(code)
        profile = fetch_github_profile(access_token)
        user, created = find_or_create_user(db, profile)
    except GitHubAccountConflictError:
        redirect = _frontend_redirect("/login", error="github_email_in_use")
        _clear_github_state_cookie(redirect)
        return redirect
    except GitHubOAuthError:
        record_audit(db, request, "AUTH_GITHUB_OAUTH_FAILED")
        db.commit()
        redirect = _frontend_redirect("/login", error="github_oauth_failed")
        _clear_github_state_cookie(redirect)
        return redirect

    if not user.is_active:
        redirect = _frontend_redirect("/login", error="account_inactive")
        _clear_github_state_cookie(redirect)
        return redirect

    auth_session, raw_token, csrf_token = create_session(db, user, request)
    record_audit(
        db,
        request,
        "AUTH_REGISTER_SUCCESS" if created else "AUTH_LOGIN_SUCCESS",
        user_id=user.id,
        details={"provider": "github", "session_id": auth_session.id},
    )
    db.commit()

    redirect = _frontend_redirect("/dashboard")
    set_auth_cookies(redirect, raw_token, csrf_token)
    _clear_github_state_cookie(redirect)
    return redirect
