"""Widen agent_skills contract_ref columns from 200 to 500 chars.

Found running real end-to-end scenarios against PostgreSQL for M7 evidence
gathering (RFC roadmap): every shipped Agent Skill fixture's
output_contract_ref is 205 chars, exceeding the old VARCHAR(200) limit.
SQLite (used by the test suite) never enforced the length, so this went
undetected until tested against the real database engine.

Revision ID: 0007_widen_contract_refs
Revises: 0006_consolidated_response
Create Date: 2026-08-26
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0007_widen_contract_refs"
down_revision: str | None = "0006_consolidated_response"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "agent_skills", "input_contract_ref", existing_type=sa.String(length=200), type_=sa.String(length=500)
    )
    op.alter_column(
        "agent_skills", "output_contract_ref", existing_type=sa.String(length=200), type_=sa.String(length=500)
    )


def downgrade() -> None:
    op.alter_column(
        "agent_skills", "output_contract_ref", existing_type=sa.String(length=500), type_=sa.String(length=200)
    )
    op.alter_column(
        "agent_skills", "input_contract_ref", existing_type=sa.String(length=500), type_=sa.String(length=200)
    )
