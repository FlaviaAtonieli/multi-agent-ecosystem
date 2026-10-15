"""Add clan settings: is_open, skills_policy, members_policy.

Clãs passam a ser configurados na criação: aberto (qualquer usuário entra
sozinho) ou fechado (só entra se adicionado), e quem pode registrar Agent
Skills CLAN / adicionar e remover membros -- "ALL_MEMBERS" ou "OWNER_ONLY"
(o dono é created_by_id). Os defaults preservam o comportamento da 0013 para
todo clã já existente: fechado, qualquer membro gerencia tudo.

Revision ID: 0015_clan_settings
Revises: 0014_google_oauth
Create Date: 2026-10-14
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0015_clan_settings"
down_revision: str | None = "0014_google_oauth"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "clans", sa.Column("is_open", sa.Boolean(), server_default=sa.false(), nullable=False)
    )
    op.add_column(
        "clans",
        sa.Column("skills_policy", sa.String(length=20), server_default="ALL_MEMBERS", nullable=False),
    )
    op.add_column(
        "clans",
        sa.Column("members_policy", sa.String(length=20), server_default="ALL_MEMBERS", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("clans", "members_policy")
    op.drop_column("clans", "skills_policy")
    op.drop_column("clans", "is_open")
