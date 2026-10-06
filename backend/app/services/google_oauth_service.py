from dataclasses import dataclass
from urllib.parse import urlencode

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import normalize_email
from app.models import User

GOOGLE_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"


class GoogleOAuthError(RuntimeError):
    """Any failure talking to Google (network, malformed response, unverified
    email). The callback endpoint catches this and redirects to the frontend
    with a generic error -- internals never reach the browser."""


class GoogleAccountConflictError(RuntimeError):
    """The verified Google email already belongs to an account not linked to
    that google_id. Same reasoning as GitHubAccountConflictError (see
    github_oauth_service.py): no silent auto-link by email, since this app
    doesn't verify emails at password registration -- auto-linking would let
    anyone claim an existing account just by registering its email first."""


@dataclass
class GoogleProfile:
    google_id: str
    name: str
    email: str
    avatar_url: str | None


def build_authorize_url(state: str) -> str:
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_oauth_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
    }
    return f"{GOOGLE_AUTHORIZE_URL}?{urlencode(params)}"


def exchange_code_for_access_token(code: str) -> str:
    try:
        response = httpx.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret_value,
                "code": code,
                "redirect_uri": settings.google_oauth_redirect_uri,
                "grant_type": "authorization_code",
            },
            headers={"Accept": "application/json"},
            timeout=10,
        )
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise GoogleOAuthError("Falha ao trocar o código de autorização com o Google.") from exc

    access_token = payload.get("access_token")
    if not access_token:
        raise GoogleOAuthError(
            payload.get("error_description") or "O Google não retornou um access_token."
        )
    return access_token


def fetch_google_profile(access_token: str) -> GoogleProfile:
    try:
        response = httpx.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        response.raise_for_status()
        raw_profile = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise GoogleOAuthError("Falha ao consultar o perfil no Google.") from exc

    profile: dict = raw_profile if isinstance(raw_profile, dict) else {}

    email = profile.get("email")
    # email_verified vem como bool (as vezes string "true"/"false" dependendo
    # do endpoint) -- normaliza antes de checar.
    email_verified = str(profile.get("email_verified", "")).lower() in {"true", "1"}
    if not email or not email_verified:
        raise GoogleOAuthError(
            "Sua conta do Google não tem um e-mail verificado acessível com a permissão concedida."
        )

    sub = profile.get("sub")
    if not sub:
        raise GoogleOAuthError("O Google não retornou um identificador de perfil (sub).")

    return GoogleProfile(
        google_id=str(sub),
        name=profile.get("name") or email.split("@")[0],
        email=normalize_email(email),
        avatar_url=profile.get("picture"),
    )


def find_or_create_user(db: Session, profile: GoogleProfile) -> tuple[User, bool]:
    """Returns (user, created). Mirrors github_oauth_service.find_or_create_user:
    matches by google_id first (stable across email/name changes), only ever
    creates a new row when no account -- neither Google-linked, GitHub-linked,
    nor password-based -- already owns that email."""
    existing_by_google = db.scalar(select(User).where(User.google_id == profile.google_id))
    if existing_by_google is not None:
        existing_by_google.name = profile.name
        existing_by_google.avatar_url = profile.avatar_url
        return existing_by_google, False

    existing_by_email = db.scalar(select(User).where(User.email == profile.email))
    if existing_by_email is not None:
        raise GoogleAccountConflictError(
            "Já existe uma conta com este e-mail. Entre com e-mail e senha."
        )

    if not settings.allow_registration:
        raise GoogleOAuthError("Novos cadastros estão desativados.")

    user = User(
        name=profile.name,
        email=profile.email,
        password_hash=None,
        google_id=profile.google_id,
        avatar_url=profile.avatar_url,
        role="USER",
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user, True
