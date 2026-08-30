"""Add follow_up_exchanges table.

Lets a user keep asking questions after the initial orchestration
execution (optionally targeting one specific Agent Skill domain), with
each round kept as its own row -- distinct from consolidated_responses
(one per TechnicalRequest, the RFC §5.3 single "resposta final"), a
request can accumulate many follow-up exchanges, preserving history.

Revision ID: 0009_follow_up_exchanges
Revises: 0008_user_onboarding
Create Date: 2026-08-29
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0009_follow_up_exchanges"
down_revision: str | None = "0008_user_onboarding"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "follow_up_exchanges",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("technical_request_id", sa.String(length=36), nullable=False),
        sa.Column("trace_id", sa.String(length=40), nullable=False),
        sa.Column("asked_by_id", sa.String(length=36), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("target_domain", sa.String(length=60), nullable=True),
        sa.Column("synthesis", sa.Text(), nullable=False),
        sa.Column("results", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("overall_confidence_level", sa.String(length=10), nullable=False),
        sa.Column("quality_gate_approved", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("requires_human_review", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["technical_request_id"], ["technical_requests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["asked_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_follow_up_exchanges_technical_request_id",
        "follow_up_exchanges",
        ["technical_request_id"],
    )
    op.create_index("ix_follow_up_exchanges_trace_id", "follow_up_exchanges", ["trace_id"])
    op.create_index("ix_follow_up_exchanges_asked_by_id", "follow_up_exchanges", ["asked_by_id"])


def downgrade() -> None:
    op.drop_index("ix_follow_up_exchanges_asked_by_id", table_name="follow_up_exchanges")
    op.drop_index("ix_follow_up_exchanges_trace_id", table_name="follow_up_exchanges")
    op.drop_index("ix_follow_up_exchanges_technical_request_id", table_name="follow_up_exchanges")
    op.drop_table("follow_up_exchanges")
