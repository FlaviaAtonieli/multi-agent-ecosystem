"""Add users.onboarding_completed_at.

Persists whether a user has finished (or skipped) the first-access
onboarding tour, so it survives across devices/browsers instead of living
only in localStorage (frontend redesign spec section 8, open item 4:
"recomendacao: backend, para persistir entre dispositivos").

Revision ID: 0008_user_onboarding
Revises: 0007_widen_contract_refs
Create Date: 2026-08-28
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0008_user_onboarding"
down_revision: str | None = "0007_widen_contract_refs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users", sa.Column("onboarding_completed_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("users", "onboarding_completed_at")
