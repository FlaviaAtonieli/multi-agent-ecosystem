"""Comitê escolhe se a busca inclui a base global de exemplo.

Os comitês que já existem continuam usando a base global, como antes.

Revision ID: 0025_clan_global_knowledge
Revises: 0024_clan_repositories
Create Date: 2026-11-23
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0025_clan_global_knowledge"
down_revision: str | None = "0024_clan_repositories"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "clans",
        sa.Column("use_global_knowledge", sa.Boolean(), server_default=sa.true(), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("clans", "use_global_knowledge")
