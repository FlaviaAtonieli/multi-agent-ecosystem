"""E-mail de conta criada, enviado a todo cadastro novo (formulário, GitHub ou Google).

Roda depois da resposta (BackgroundTasks), então não atrasa o cadastro, e uma
falha no envio só fica no log: a conta já existe e funciona sem o e-mail. Também
serve de alerta para quem não pediu a conta, se alguém usou o e-mail dela.
"""

import logging

from app.core.config import settings
from app.services.email_service import EmailDeliveryError, send_email

logger = logging.getLogger(__name__)


def send_welcome_email(*, to: str, name: str) -> None:
    try:
        send_email(
            to=to,
            subject=f"Sua conta no {settings.app_name} foi criada",
            body=(
                f"Olá, {name}.\n\n"
                f"Sua conta no {settings.app_name} foi criada com este e-mail. "
                f"Para entrar, acesse:\n\n{settings.frontend_base_url}/login\n\n"
                "Se não foi você que criou esta conta, alguém usou o seu e-mail. Use \"Esqueci minha "
                "senha\" na tela de login para assumir a conta e, em Configurações, exclua-a."
            ),
        )
    except EmailDeliveryError:
        logger.warning("E-mail de conta criada não enviado para %s.", to)
