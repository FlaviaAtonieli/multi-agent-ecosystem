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
    """Qualquer falha ao falar com o GitHub (rede, resposta malformada, sem e-mail
    utilizável). O callback redireciona com um erro genérico; os detalhes nunca chegam
    ao navegador.
    """


class GitHubAccountConflictError(RuntimeError):
    """O e-mail verificado no GitHub já é de outra conta, não ligada a esse github_id.

    Não há ligação automática pelo e-mail: o cadastro com senha não verifica o e-mail,
    então bastaria cadastrar antes o e-mail de alguém para tomar a conta. Ainda não há
    fluxo para ligar contas; a pessoa entra com a senha da conta existente.
    """


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

    email = profile.get("email")
    if not email:
        # Sem email publico -- busca a lista de emails da conta (requer o
        # escopo user:email) e usa o primario verificado; na falta dele,
        # qualquer email verificado.
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
    """Devolve (usuário, criado). Procura primeiro pelo github_id, que não muda quando
    a pessoa troca nome ou e-mail no GitHub. Só cria uma conta nova quando nenhuma
    outra já usa aquele e-mail.
    """
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
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user, True
