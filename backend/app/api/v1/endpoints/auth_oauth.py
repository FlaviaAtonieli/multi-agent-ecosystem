"""Login com GitHub e com Google (OAuth 2.0), um fluxo só para os dois provedores."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.v1.endpoints.auth import open_login_challenge
from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import github_oauth_rate_limit, google_oauth_rate_limit
from app.core.security import generate_csrf_token, secure_compare
from app.models import User
from app.services.audit_service import record_audit
from app.services.email_service import EmailDeliveryError
from app.services.github_oauth_service import (
    GitHubAccountConflictError,
    GitHubOAuthError,
    build_authorize_url,
    exchange_code_for_access_token,
    fetch_github_profile,
    find_or_create_user,
)
from app.services.google_oauth_service import (
    GoogleAccountConflictError,
    GoogleOAuthError,
    fetch_google_profile,
)
from app.services.google_oauth_service import build_authorize_url as build_google_authorize_url
from app.services.google_oauth_service import (
    exchange_code_for_access_token as exchange_google_code_for_access_token,
)
from app.services.google_oauth_service import find_or_create_user as find_or_create_google_user
from app.services.login_verification_service import requires_login_code, set_login_challenge_cookie
from app.services.session_service import create_session, set_auth_cookies
from app.services.welcome_email_service import send_welcome_email

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@dataclass(frozen=True)
class _Provider:
    name: str  # "github" ou "google": rota, cookie, auditoria e erros na tela
    label: str
    enabled: Callable[[], bool]
    authorize_url: Callable[[str], str]
    # Perfil a partir do código devolvido pelo provedor, e conta a partir do perfil.
    profile_from_code: Callable[[str], Any]
    find_or_create: Callable[[Session, Any], tuple[User, bool]]
    conflict_error: type[Exception]
    oauth_error: type[Exception]

    @property
    def state_cookie(self) -> str:
        return f"agenthub_{self.name}_oauth_state"

    @property
    def cookie_path(self) -> str:
        return f"{settings.api_v1_prefix}/auth/{self.name}"


# As funções do provedor são buscadas na hora da chamada, para os testes poderem
# trocá-las neste módulo.
_GITHUB = _Provider(
    name="github",
    label="GitHub",
    enabled=lambda: settings.github_oauth_enabled,
    authorize_url=lambda state: build_authorize_url(state),
    profile_from_code=lambda code: fetch_github_profile(exchange_code_for_access_token(code)),
    find_or_create=lambda db, profile: find_or_create_user(db, profile),
    conflict_error=GitHubAccountConflictError,
    oauth_error=GitHubOAuthError,
)
_GOOGLE = _Provider(
    name="google",
    label="Google",
    enabled=lambda: settings.google_oauth_enabled,
    authorize_url=lambda state: build_google_authorize_url(state),
    profile_from_code=lambda code: fetch_google_profile(exchange_google_code_for_access_token(code)),
    find_or_create=lambda db, profile: find_or_create_google_user(db, profile),
    conflict_error=GoogleAccountConflictError,
    oauth_error=GoogleOAuthError,
)


def _redirect(provider: _Provider, path: str, **query: str) -> RedirectResponse:
    url = f"{settings.frontend_base_url}{path}"
    if query:
        url = f"{url}?{urlencode(query)}"
    response = RedirectResponse(url, status_code=status.HTTP_302_FOUND)
    response.delete_cookie(provider.state_cookie, path=provider.cookie_path)
    return response


def _require_enabled(provider: _Provider) -> None:
    if not provider.enabled():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Login com {provider.label} não está habilitado."
        )


def _start(provider: _Provider) -> RedirectResponse:
    """Manda para a tela de autorização do provedor. O `state` é a proteção contra CSRF
    do próprio OAuth: o CSRF da sessão não serve aqui, porque esta etapa é uma navegação
    do navegador. Ele fica num cookie curto e é conferido no retorno."""
    _require_enabled(provider)
    state = generate_csrf_token()
    redirect = RedirectResponse(provider.authorize_url(state), status_code=status.HTTP_302_FOUND)
    redirect.set_cookie(
        key=provider.state_cookie,
        value=state,
        max_age=600,
        path=provider.cookie_path,
        secure=settings.cookie_secure,
        httponly=True,
        samesite="lax",
    )
    return redirect


def _finish(
    provider: _Provider,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session,
    code: str | None,
    state: str | None,
) -> RedirectResponse:
    _require_enabled(provider)
    audit_prefix = f"AUTH_{provider.name.upper()}"
    failed = f"{provider.name}_oauth_failed"

    cookie_state = request.cookies.get(provider.state_cookie)
    if not code or not state or not cookie_state or not secure_compare(state, cookie_state):
        record_audit(db, request, f"{audit_prefix}_STATE_MISMATCH")
        db.commit()
        return _redirect(provider, "/login", error=failed)

    try:
        user, created = provider.find_or_create(db, provider.profile_from_code(code))
    except provider.conflict_error:
        return _redirect(provider, "/login", error=f"{provider.name}_email_in_use")
    except provider.oauth_error:
        record_audit(db, request, f"{audit_prefix}_OAUTH_FAILED")
        db.commit()
        return _redirect(provider, "/login", error=failed)

    if not user.is_active:
        return _redirect(provider, "/login", error="account_inactive")

    if requires_login_code(db, request, user):
        if created:
            record_audit(
                db, request, "AUTH_REGISTER_SUCCESS", user_id=user.id, details={"provider": provider.name}
            )
        try:
            challenge_token = open_login_challenge(db, request, user, provider.name)
        except EmailDeliveryError:
            return _redirect(provider, "/login", error="login_code_failed")
        if created:
            background_tasks.add_task(send_welcome_email, to=user.email, name=user.name)
        redirect = _redirect(provider, "/login", verify="1")
        set_login_challenge_cookie(redirect, challenge_token)
        return redirect

    auth_session, raw_token, csrf_token = create_session(db, user, request)
    record_audit(
        db,
        request,
        "AUTH_REGISTER_SUCCESS" if created else "AUTH_LOGIN_SUCCESS",
        user_id=user.id,
        details={"provider": provider.name, "session_id": auth_session.id},
    )
    db.commit()
    if created:
        background_tasks.add_task(send_welcome_email, to=user.email, name=user.name)
    redirect = _redirect(provider, "/dashboard")
    set_auth_cookies(redirect, raw_token, csrf_token)
    return redirect


@router.get("/github/login")
def github_login(_rate: None = Depends(github_oauth_rate_limit)) -> RedirectResponse:
    return _start(_GITHUB)


@router.get("/github/callback")
def github_callback(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    code: str | None = None,
    state: str | None = None,
    _rate: None = Depends(github_oauth_rate_limit),
) -> RedirectResponse:
    return _finish(_GITHUB, request, background_tasks, db, code, state)


@router.get("/google/login")
def google_login(_rate: None = Depends(google_oauth_rate_limit)) -> RedirectResponse:
    return _start(_GOOGLE)


@router.get("/google/callback")
def google_callback(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    code: str | None = None,
    state: str | None = None,
    _rate: None = Depends(google_oauth_rate_limit),
) -> RedirectResponse:
    return _finish(_GOOGLE, request, background_tasks, db, code, state)

