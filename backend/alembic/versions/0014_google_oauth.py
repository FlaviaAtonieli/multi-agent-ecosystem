"""Add Google OAuth field to users (google_id), mirroring 0011_github_oauth.

Login com Google passa a ser um segundo metodo de OAuth, ao lado de
email/senha e GitHub. google_id (unico) linka a conta ao `sub` do perfil
OpenID Connect do Google. Nenhuma linha existente muda: google_id fica
NULL para toda conta ja cadastrada.

Revision ID: 0014_google_oauth
Revises: 0013_clans
Create Date: 2026-10-05
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0014_google_oauth"
down_revision: str | None = "0013_clans"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("google_id", sa.String(length=255), nullable=True),
    )
    op.create_index("ix_users_google_id", "users", ["google_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_google_id", table_name="users")
    op.drop_column("users", "google_id")
