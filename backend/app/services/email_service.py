import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger(__name__)

# Mensagens enviadas pelo backend "console" -- só para dev e testes, que leem o
# código de verificação daqui em vez de uma caixa de e-mail real.
console_outbox: list[EmailMessage] = []


class EmailDeliveryError(RuntimeError):
    pass


def send_email(*, to: str, subject: str, body: str) -> None:
    message = EmailMessage()
    message["To"] = to
    message["From"] = settings.smtp_from or "no-reply@localhost"
    message["Subject"] = subject
    message.set_content(body)

    if settings.email_backend == "console":
        console_outbox.append(message)
        logger.warning("EMAIL_BACKEND=console -- e-mail para %s não enviado.\n%s\n%s", to, subject, body)
        return

    try:
        with smtplib.SMTP(settings.smtp_host or "", settings.smtp_port, timeout=15) as smtp:
            if settings.smtp_starttls:
                smtp.starttls()
            if settings.smtp_username and settings.smtp_password_value:
                smtp.login(settings.smtp_username, settings.smtp_password_value)
            smtp.send_message(message)
    except (smtplib.SMTPException, OSError) as exc:
        logger.exception("Falha ao enviar e-mail via SMTP para %s", to)
        raise EmailDeliveryError("Não foi possível enviar o e-mail agora. Tente novamente.") from exc
