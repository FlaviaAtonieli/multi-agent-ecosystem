from dataclasses import dataclass
from urllib.parse import urlencode

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import normalize_email
from app.models import User

GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"
GITHUB_USER_EMAILS_URL = "https://api.github.com/user/emails"


class GitHubOAuthError(RuntimeError):
    """Any failure talking to GitHub (network, malformed response, no usable
    email). The callback endpoint catches this and redirects to the frontend
    with a generic error -- internals never reach the browser."""


class GitHubAccountConflictError(RuntimeError):
    """The verified GitHub email already belongs to an account not linked to
    that github_id. No silent auto-link by email: this app doesn't verify
    emails at password registration, so auto-linking would let anyone claim
    an existing account just by registering its email first -- an account
    takeover path. There is no account-linking flow yet (see
    docs/integrations/github-oauth.md); the user is told to log in with the
    existing credentials instead."""


@dataclass
class GitHubProfile:
    github_id: str
    name: str
    email: str
    avatar_url: str | None


def build_authorize_url(state: str) -> str:
    params = {
        "client_id": settings.github_client_id,
        "redirect_uri": settings.github_oauth_redirect_uri,
        "scope": "read:user user:email",
        "state": state,
        "allow_signup": "true",
    }
    return f"{GITHUB_AUTHORIZE_URL}?{urlencode(params)}"


def exchange_code_for_access_token(code: str) -> str:
    try:
        response = httpx.post(
            GITHUB_TOKEN_URL,
            data={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret_value,
                "code": code,
                "redirect_uri": settings.github_oauth_redirect_uri,
            },
            headers={"Accept": "application/json"},
            timeout=10,
        )
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise GitHubOAuthError("Falha ao trocar o código de autorização com o GitHub.") from exc

    access_token = payload.get("access_token")
    if not access_token:
        raise GitHubOAuthError(
            payload.get("error_description") or "O GitHub não retornou um access_token."
        )
    return access_token


def _github_get(url: str, access_token: str) -> object:
    try:
        response = httpx.get(
            url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise GitHubOAuthError("Falha ao consultar o perfil no GitHub.") from exc


def fetch_github_profile(access_token: str) -> GitHubProfile:
    raw_profile = _github_get(GITHUB_USER_URL, access_token)
    profile: dict = raw_profile if isinstance(raw_profile, dict) else {}

    # Sempre busca a lista de e-mails da conta (requer o escopo user:email) em
    # vez de confiar no campo "email" de /user: esse campo é o e-mail público
    # do perfil e não tem garantia de estar marcado como verified pela API --
    # usá-lo sem checar abriria uma via pra alguém reivindicar/criar uma conta
    # com um e-mail que não controla de fato (mesma classe de risco que
    # find_or_create_user já evita ao recusar auto-link por e-mail).
    raw_emails = _github_get(GITHUB_USER_EMAILS_URL, access_token)
    candidates: list[dict] = raw_emails if isinstance(raw_emails, list) else []
    primary = next((e for e in candidates if e.get("primary") and e.get("verified")), None)
    chosen = primary or next((e for e in candidates if e.get("verified")), None)
    email = chosen["email"] if chosen else None

    if not email:
        raise GitHubOAuthError(
            "Sua conta do GitHub não tem nenhum e-mail verificado acessível "
            "com a permissão concedida."
        )

    return GitHubProfile(
        github_id=str(profile["id"]),
        name=profile.get("name") or profile.get("login") or "Usuário GitHub",
        email=normalize_email(email),
        avatar_url=profile.get("avatar_url"),
    )


def find_or_create_user(db: Session, profile: GitHubProfile) -> tuple[User, bool]:
    """Returns (user, created). Matches by github_id first (stable across
    email/name changes on GitHub); only ever creates a new row when no
    account -- neither GitHub-linked nor password-based -- already owns that
    email."""
    existing_by_github = db.scalar(select(User).where(User.github_id == profile.github_id))
    if existing_by_github is not None:
        existing_by_github.name = profile.name
        existing_by_github.avatar_url = profile.avatar_url
        return existing_by_github, False

    existing_by_email = db.scalar(select(User).where(User.email == profile.email))
    if existing_by_email is not None:
        raise GitHubAccountConflictError(
            "Já existe uma conta com este e-mail. Entre com e-mail e senha."
        )

    if not settings.allow_registration:
        raise GitHubOAuthError("Novos cadastros estão desativados.")

    user = User(
        name=profile.name,
        email=profile.email,
        password_hash=None,
        github_id=profile.github_id,
        avatar_url=profile.avatar_url,
        role="USER",
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user, True
