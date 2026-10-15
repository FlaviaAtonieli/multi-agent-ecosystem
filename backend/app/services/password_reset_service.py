"""Esqueci minha senha: link de uso único enviado ao e-mail cadastrado."""

from datetime import timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import generate_session_token, hash_password, hash_token, utc_now
from app.models import PasswordResetToken, User
from app.services.email_service import send_email
from app.services.login_verification_service import as_utc, revoke_trusted_devices
from app.services.session_service import revoke_all_sessions


class PasswordResetTokenError(ValueError):
    pass


def request_password_reset(db: Session, user: User) -> None:
    """Invalida os links anteriores do usuário e envia um novo. Quem chama não
    revela ao cliente se o e-mail existe (resposta sempre igual)."""
    now = utc_now()
    db.execute(
        update(PasswordResetToken)
        .where(PasswordResetToken.user_id == user.id, PasswordResetToken.used_at.is_(None))
        .values(used_at=now)
    )
    raw_token = generate_session_token()
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=hash_token(raw_token),
            expires_at=now + timedelta(minutes=settings.password_reset_ttl_minutes),
        )
    )
    db.flush()

    link = f"{settings.frontend_base_url}/reset-password?token={raw_token}"
    send_email(
        to=user.email,
        subject="Redefinição de senha",
        body=(
            f"Olá, {user.name}.\n\n"
            "Recebemos um pedido para redefinir a senha da sua conta no Multi-Agent Ecosystem. "
            f"Para escolher uma nova senha, acesse:\n\n{link}\n\n"
            f"O link vale por {settings.password_reset_ttl_minutes} minutos e só pode ser usado uma vez. "
            "Se não foi você, ignore este e-mail: sua senha atual continua valendo."
        ),
    )


def reset_password(db: Session, *, raw_token: str, new_password: str) -> User:
    token = db.scalar(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == hash_token(raw_token))
    )
    if token is None or token.used_at is not None or as_utc(token.expires_at) <= utc_now():
        raise PasswordResetTokenError("Este link de redefinição é inválido ou expirou. Peça um novo.")
    user = db.get(User, token.user_id)
    if user is None or not user.is_active:
        raise PasswordResetTokenError("Este link de redefinição é inválido ou expirou. Peça um novo.")

    token.used_at = utc_now()
    user.password_hash = hash_password(new_password)
    user.failed_login_attempts = 0
    user.locked_until = None
    # Quem redefine a senha pode estar recuperando uma conta comprometida:
    # derruba todas as sessões e exige código de novo em todo navegador.
    revoke_all_sessions(db, user.id)
    revoke_trusted_devices(db, user.id)
    db.flush()
    return user
