"""Drop users.role: todos os usuários passam a ter as mesmas permissões.

Os papéis USER/TECHNICIAN/REVIEWER/ADMIN foram removidos para simplificar o
uso: qualquer usuário cria e gerencia as próprias Agent Skills (inclusive
OFFICIAL), revisa as próprias solicitações sinalizadas e vê só a própria
trilha de auditoria. O painel de administração saiu junto.

Revision ID: 0016_drop_user_roles
Revises: 0015_clan_settings
Create Date: 2026-10-14
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0016_drop_user_roles"
down_revision: str | None = "0015_clan_settings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("users", "role")


def downgrade() -> None:
    # Volta todo mundo como USER -- os papéis anteriores não são recuperáveis.
    op.add_column(
        "users",
        sa.Column("role", sa.String(length=20), server_default="USER", nullable=False),
    )
