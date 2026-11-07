
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response, status
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
    login_code_rate_limit,
    login_rate_limit,
    password_reset_rate_limit,
    register_rate_limit,
    renew_rate_limit,
)
from app.core.security import (
    generate_csrf_token,
    hash_password,
    is_initial_account,
    normalize_email,
    utc_now,
    verify_password,
)
from app.models import AuthSession, User
from app.schemas.auth import (
    AuthResponse,
    CsrfResponse,
    LoginChallengeResponse,
    LoginCodeVerify,
    LoginRequest,
    SessionRead,
)
from app.schemas.user import (
    PasswordChange,
    PasswordForgot,
    PasswordReset,
    UserCreate,
    UserNameUpdate,
    UserRead,
)
from app.services.audit_service import record_audit
from app.services.auth_service import authenticate_user
from app.services.email_service import EmailDeliveryError
from app.services.login_verification_service import (
    LOGIN_CHALLENGE_COOKIE,
    LoginChallengeError,
    LoginCodeIncorrectError,
    LoginCodeResendTooSoonError,
    clear_login_challenge_cookie,
    get_open_challenge,
    mask_email,
    requires_login_code,
    resend_login_code,
    revoke_trusted_devices,
    set_login_challenge_cookie,
    set_trusted_device_cookie,
    start_login_challenge,
    trust_device,
    verify_login_code,
)
from app.services.password_reset_service import (
    PasswordResetTokenError,
    request_password_reset,
    reset_password,
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
from app.services.welcome_email_service import send_welcome_email

router = APIRouter(prefix="/auth", tags=["Autenticação"])



def _to_user_read(user: User) -> UserRead:
    """UserRead.model_validate(user) alone would silently report has_password=False
    for everyone (it isn't a real column, just a default) -- every response that
    serializes a User must go through here instead."""
    data = UserRead.model_validate(user).model_dump()
    data["has_password"] = user.password_hash is not None
    data["oauth_provider"] = "github" if user.github_id else "google" if user.google_id else None
    data["is_initial_account"] = is_initial_account(user.email)
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
    background_tasks: BackgroundTasks,
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
    background_tasks.add_task(send_welcome_email, to=user.email, name=user.name)
    return AuthResponse(user=_to_user_read(user), session_expires_at=auth_session.expires_at)


def open_login_challenge(db: Session, request: Request, user: User, provider: str) -> str:
    """Abre o desafio de código por e-mail e retorna o token do cookie. Falha
    de envio vira EmailDeliveryError para cada chamador tratar do seu jeito."""
    try:
        raw_token = start_login_challenge(db, user=user, provider=provider)
    except EmailDeliveryError:
        db.rollback()
        raise
    record_audit(db, request, "AUTH_LOGIN_CODE_SENT", user_id=user.id, details={"provider": provider})
    db.commit()
    return raw_token


@router.post(
    "/login",
    response_model=AuthResponse | LoginChallengeResponse,
    responses={202: {"model": LoginChallengeResponse}},
)
def login(
    request: Request,
    response: Response,
    payload: LoginRequest,
    db: Session = Depends(get_db),
    _csrf: None = Depends(require_public_csrf),
    _rate: None = Depends(login_rate_limit),
) -> AuthResponse | LoginChallengeResponse:
    user = authenticate_user(db, request, str(payload.email), payload.password)
    if requires_login_code(db, request, user):
        try:
            raw_token = open_login_challenge(db, request, user, "password")
        except EmailDeliveryError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
        set_login_challenge_cookie(response, raw_token)
        response.status_code = status.HTTP_202_ACCEPTED
        return LoginChallengeResponse(email_hint=mask_email(user.email))

    auth_session, raw_token, csrf_token = create_session(db, user, request)
    record_audit(db, request, "AUTH_LOGIN_SUCCESS", user_id=user.id, details={"session_id": auth_session.id})
    db.commit()
    db.refresh(user)
    db.refresh(auth_session)

    set_auth_cookies(response, raw_token, csrf_token)
    return AuthResponse(user=_to_user_read(user), session_expires_at=auth_session.expires_at)


@router.get("/login/challenge", response_model=LoginChallengeResponse)
def login_challenge_status(request: Request, db: Session = Depends(get_db)) -> LoginChallengeResponse:
    """Usado pela tela de código depois do redirect do GitHub/Google: diz se há
    um login pendente neste navegador e para qual e-mail o código foi."""
    try:
        challenge = get_open_challenge(db, request.cookies.get(LOGIN_CHALLENGE_COOKIE))
    except LoginChallengeError as exc:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail=str(exc)) from exc
    user = db.get(User, challenge.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Entre novamente.")
    return LoginChallengeResponse(email_hint=mask_email(user.email))


@router.post("/login/verify", response_model=AuthResponse)
def verify_login(
    request: Request,
    response: Response,
    payload: LoginCodeVerify,
    db: Session = Depends(get_db),
    _csrf: None = Depends(require_public_csrf),
    _rate: None = Depends(login_code_rate_limit),
) -> AuthResponse:
    try:
        user, challenge = verify_login_code(
            db, raw_token=request.cookies.get(LOGIN_CHALLENGE_COOKIE), code=payload.code
        )
    except LoginCodeIncorrectError as exc:
        record_audit(db, request, "AUTH_LOGIN_CODE_FAILED")
        db.commit()  # persiste a tentativa antes de responder
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except LoginChallengeError as exc:
        db.commit()
        raise HTTPException(status_code=status.HTTP_410_GONE, detail=str(exc)) from exc

    auth_session, raw_token, csrf_token = create_session(db, user, request)
    device_token = trust_device(db, user=user, request=request)
    record_audit(
        db,
        request,
        "AUTH_LOGIN_SUCCESS",
        user_id=user.id,
        details={"session_id": auth_session.id, "provider": challenge.provider, "login_code": True},
    )
    db.commit()
    db.refresh(user)
    db.refresh(auth_session)

    set_auth_cookies(response, raw_token, csrf_token)
    set_trusted_device_cookie(response, device_token)
    clear_login_challenge_cookie(response)
    return AuthResponse(user=_to_user_read(user), session_expires_at=auth_session.expires_at)


@router.post("/login/resend", response_model=LoginChallengeResponse)
def resend_login(
    request: Request,
    db: Session = Depends(get_db),
    _csrf: None = Depends(require_public_csrf),
    _rate: None = Depends(login_code_rate_limit),
) -> LoginChallengeResponse:
    try:
        user = resend_login_code(db, raw_token=request.cookies.get(LOGIN_CHALLENGE_COOKIE))
    except LoginCodeResendTooSoonError as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)) from exc
    except LoginChallengeError as exc:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail=str(exc)) from exc
    except EmailDeliveryError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    record_audit(db, request, "AUTH_LOGIN_CODE_SENT", user_id=user.id, details={"resend": True})
    db.commit()
    return LoginChallengeResponse(email_hint=mask_email(user.email))


@router.post("/password/forgot", status_code=status.HTTP_202_ACCEPTED)
def forgot_password(
    request: Request,
    payload: PasswordForgot,
    db: Session = Depends(get_db),
    _csrf: None = Depends(require_public_csrf),
    _rate: None = Depends(password_reset_rate_limit),
) -> dict[str, str]:
    """Resposta sempre igual, exista ou não a conta (não revela e-mails
    cadastrados). Contas só com GitHub/Google não têm senha para redefinir."""
    if settings.is_production and settings.email_backend == "console":
        # Sem SMTP, o link não sai: melhor dizer isso do que prometer um e-mail
        # que não vai chegar. A resposta é igual para qualquer e-mail.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="A recuperação de senha por e-mail não está configurada neste ambiente.",
        )
    user = db.scalar(select(User).where(User.email == normalize_email(str(payload.email))))
    if user is not None and user.is_active and user.password_hash is not None:
        try:
            request_password_reset(db, user)
        except EmailDeliveryError as exc:
            db.rollback()
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
        record_audit(db, request, "AUTH_PASSWORD_RESET_REQUESTED", user_id=user.id)
        db.commit()
    return {"message": "Se o e-mail estiver cadastrado, você vai receber um link para redefinir a senha."}


@router.post("/password/reset", status_code=status.HTTP_204_NO_CONTENT)
def reset_forgotten_password(
    request: Request,
    payload: PasswordReset,
    db: Session = Depends(get_db),
    _csrf: None = Depends(require_public_csrf),
    _rate: None = Depends(password_reset_rate_limit),
) -> Response:
    try:
        user = reset_password(db, raw_token=payload.token, new_password=payload.new_password)
    except PasswordResetTokenError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    record_audit(db, request, "AUTH_PASSWORD_RESET_COMPLETED", user_id=user.id)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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
    revoke_trusted_devices(db, current_session.user_id)
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
    revoke_trusted_devices(db, user.id)
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
    user.google_id = None
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
