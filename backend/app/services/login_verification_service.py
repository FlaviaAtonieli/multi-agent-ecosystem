"""Código de login por e-mail, pedido só em dispositivo/navegador novo.

Fluxo: o login (senha, GitHub ou Google) valida a identidade como antes; se o
navegador não traz um cookie de dispositivo confiável válido para esse usuário,
em vez de criar a sessão abre-se um LoginChallenge e um código de 6 dígitos vai
para o e-mail cadastrado. Confirmar o código cria a sessão e marca o navegador
como confiável por TRUSTED_DEVICE_DAYS.
"""

import secrets
from datetime import datetime, timedelta

from fastapi import Request, Response
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import ensure_utc, generate_session_token, hash_token, secure_compare, utc_now
from app.models import LoginChallenge, TrustedDevice, User
from app.services.audit_service import get_user_agent
from app.services.email_service import send_email

LOGIN_CHALLENGE_COOKIE = "agenthub_login_challenge"
TRUSTED_DEVICE_COOKIE = "agenthub_trusted_device"

_TOO_MANY_ATTEMPTS = "Muitas tentativas incorretas. Entre novamente para receber outro código."


def as_utc(value: datetime) -> datetime:
    """ensure_utc para colunas NOT NULL (o SQLite devolve datetimes sem fuso)."""
    converted = ensure_utc(value)
    assert converted is not None
    return converted


class LoginChallengeError(ValueError):
    """Desafio ausente, expirado, já usado ou com tentativas esgotadas: o
    usuário precisa fazer login de novo."""


class LoginCodeIncorrectError(ValueError):
    def __init__(self, remaining_attempts: int) -> None:
        self.remaining_attempts = remaining_attempts
        super().__init__(
            f"Código incorreto. Você ainda tem {remaining_attempts} "
            f"tentativa{'s' if remaining_attempts != 1 else ''}."
        )


class LoginCodeResendTooSoonError(ValueError):
    def __init__(self, wait_seconds: int) -> None:
        self.wait_seconds = wait_seconds
        super().__init__(f"Aguarde {wait_seconds}s para pedir um novo código.")


def _cookie_path() -> str:
    # Só as rotas de autenticação precisam ler esses cookies (login, callbacks
    # OAuth e /login/verify|resend|challenge).
    return f"{settings.api_v1_prefix}/auth"


def mask_email(email: str) -> str:
    local, _, domain = email.partition("@")
    visible = local[:2] if len(local) > 2 else local[:1]
    return f"{visible}{'*' * max(3, len(local) - len(visible))}@{domain}"


def requires_login_code(db: Session, request: Request, user: User) -> bool:
    if not settings.login_email_code_enabled:
        return False
    raw_token = request.cookies.get(TRUSTED_DEVICE_COOKIE)
    if not raw_token:
        return True
    device = db.scalar(
        select(TrustedDevice).where(
            TrustedDevice.token_hash == hash_token(raw_token), TrustedDevice.user_id == user.id
        )
    )
    now = utc_now()
    if device is None or as_utc(device.expires_at) <= now:
        return True
    device.last_used_at = now
    return False


def _code_hash(token_hash: str, code: str) -> str:
    return hash_token(f"{token_hash}:{code}")


def _send_code(user: User, code: str) -> None:
    send_email(
        to=user.email,
        subject=f"{code} é o seu código de acesso",
        body=(
            f"Olá, {user.name}.\n\n"
            f"Seu código para entrar no Multi-Agent Ecosystem é: {code}\n\n"
            f"Ele vale por {settings.login_code_ttl_minutes} minutos. Se não foi você quem tentou "
            "entrar, ignore este e-mail e troque sua senha."
        ),
    )


def start_login_challenge(db: Session, *, user: User, provider: str) -> str:
    """Abre um desafio (invalidando os anteriores do usuário) e envia o código.
    Retorna o token cru do cookie que amarra o desafio a este navegador."""
    now = utc_now()
    db.execute(
        update(LoginChallenge)
        .where(LoginChallenge.user_id == user.id, LoginChallenge.consumed_at.is_(None))
        .values(consumed_at=now)
    )

    raw_token = generate_session_token()
    token_hash = hash_token(raw_token)
    code = f"{secrets.randbelow(1_000_000):06d}"
    db.add(
        LoginChallenge(
            user_id=user.id,
            token_hash=token_hash,
            code_hash=_code_hash(token_hash, code),
            provider=provider,
            expires_at=now + timedelta(minutes=settings.login_code_ttl_minutes),
            last_sent_at=now,
        )
    )
    db.flush()
    _send_code(user, code)
    return raw_token


def get_open_challenge(db: Session, raw_token: str | None) -> LoginChallenge:
    if not raw_token:
        raise LoginChallengeError("Nenhum login pendente de confirmação. Entre novamente.")
    challenge = db.scalar(select(LoginChallenge).where(LoginChallenge.token_hash == hash_token(raw_token)))
    if challenge is None or challenge.consumed_at is not None:
        raise LoginChallengeError("Nenhum login pendente de confirmação. Entre novamente.")
    if as_utc(challenge.expires_at) <= utc_now():
        raise LoginChallengeError("O código expirou. Entre novamente para receber outro.")
    if challenge.attempts >= settings.login_code_max_attempts:
        raise LoginChallengeError(_TOO_MANY_ATTEMPTS)
    return challenge


def verify_login_code(db: Session, *, raw_token: str | None, code: str) -> tuple[User, LoginChallenge]:
    challenge = get_open_challenge(db, raw_token)
    if not secure_compare(_code_hash(challenge.token_hash, code.strip()), challenge.code_hash):
        challenge.attempts += 1
        remaining = settings.login_code_max_attempts - challenge.attempts
        if remaining <= 0:
            challenge.consumed_at = utc_now()
            raise LoginChallengeError(_TOO_MANY_ATTEMPTS)
        raise LoginCodeIncorrectError(remaining)

    challenge.consumed_at = utc_now()
    user = db.get(User, challenge.user_id)
    if user is None or not user.is_active:
        raise LoginChallengeError("Esta conta não possui acesso ao sistema.")
    return user, challenge


def resend_login_code(db: Session, *, raw_token: str | None) -> User:
    challenge = get_open_challenge(db, raw_token)
    now = utc_now()
    elapsed = (now - as_utc(challenge.last_sent_at)).total_seconds()
    if elapsed < settings.login_code_resend_cooldown_seconds:
        raise LoginCodeResendTooSoonError(int(settings.login_code_resend_cooldown_seconds - elapsed) + 1)

    user = db.get(User, challenge.user_id)
    if user is None or not user.is_active:
        raise LoginChallengeError("Esta conta não possui acesso ao sistema.")
    code = f"{secrets.randbelow(1_000_000):06d}"
    # attempts não zera: o limite vale por login, não por código enviado.
    challenge.code_hash = _code_hash(challenge.token_hash, code)
    challenge.last_sent_at = now
    challenge.expires_at = now + timedelta(minutes=settings.login_code_ttl_minutes)
    db.flush()
    _send_code(user, code)
    return user


def trust_device(db: Session, *, user: User, request: Request) -> str:
    raw_token = generate_session_token()
    db.add(
        TrustedDevice(
            user_id=user.id,
            token_hash=hash_token(raw_token),
            user_agent=get_user_agent(request),
            expires_at=utc_now() + timedelta(days=settings.trusted_device_days),
        )
    )
    db.flush()
    return raw_token


def revoke_trusted_devices(db: Session, user_id: str) -> None:
    """Depois de trocar a senha ou sair de todas as sessões, todo navegador
    volta a pedir código no próximo login."""
    db.query(TrustedDevice).filter(TrustedDevice.user_id == user_id).delete()


def set_login_challenge_cookie(response: Response, raw_token: str) -> None:
    response.set_cookie(
        key=LOGIN_CHALLENGE_COOKIE,
        value=raw_token,
        max_age=settings.login_code_ttl_minutes * 60,
        path=_cookie_path(),
        secure=settings.cookie_secure,
        httponly=True,
        samesite="lax",
    )


def clear_login_challenge_cookie(response: Response) -> None:
    response.delete_cookie(LOGIN_CHALLENGE_COOKIE, path=_cookie_path())


def set_trusted_device_cookie(response: Response, raw_token: str) -> None:
    response.set_cookie(
        key=TRUSTED_DEVICE_COOKIE,
        value=raw_token,
        max_age=settings.trusted_device_days * 24 * 60 * 60,
        path=_cookie_path(),
        secure=settings.cookie_secure,
        httponly=True,
        samesite="lax",
    )
