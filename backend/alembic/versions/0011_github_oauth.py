"""Add GitHub OAuth fields to users; password_hash becomes optional.

Login com GitHub passa a ser um metodo adicional, ao lado de email/senha.
Contas criadas via GitHub nao tem senha -- password_hash vira nullable, e
github_id (unico) linka a conta ao perfil do GitHub. avatar_url e usado pela
UI (topbar). Nenhuma linha existente muda: password_hash continua
preenchido pra toda conta ja cadastrada, github_id/avatar_url ficam NULL.

Revision ID: 0011_github_oauth
Revises: 0010_agent_skill_ownership
Create Date: 2026-09-16
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0011_github_oauth"
down_revision: str | None = "0010_agent_skill_ownership"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("users", "password_hash", existing_type=sa.String(length=512), nullable=True)
    op.add_column(
        "users",
        sa.Column("github_id", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("avatar_url", sa.String(length=512), nullable=True),
    )
    op.create_index("ix_users_github_id", "users", ["github_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_github_id", table_name="users")
    op.drop_column("users", "avatar_url")
    op.drop_column("users", "github_id")
    op.alter_column("users", "password_hash", existing_type=sa.String(length=512), nullable=False)
