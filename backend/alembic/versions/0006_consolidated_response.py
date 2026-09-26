"""Add consolidated response entity (RFC secao 5.3, criterio 5.5).

Revision ID: 0006_consolidated_response
Revises: 0005_agent_skills
Create Date: 2026-08-25
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0006_consolidated_response"
down_revision: str | None = "0005_agent_skills"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "consolidated_responses",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("technical_request_id", sa.String(length=36), nullable=False),
        sa.Column("trace_id", sa.String(length=40), nullable=False),
        sa.Column("technical_synthesis", sa.Text(), nullable=False),
        sa.Column("recommendations", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("risks", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("limitations", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("participating_agents", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("overall_confidence_level", sa.String(length=10), nullable=False),
        sa.Column("quality_gate_approved", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("requires_human_review", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("invocation_ids", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["technical_request_id"], ["technical_requests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("technical_request_id"),
    )
    op.create_index(
        "ix_consolidated_responses_technical_request_id",
        "consolidated_responses",
        ["technical_request_id"],
        unique=True,
    )
    op.create_index("ix_consolidated_responses_trace_id", "consolidated_responses", ["trace_id"])


def downgrade() -> None:
    op.drop_index("ix_consolidated_responses_trace_id", table_name="consolidated_responses")
    op.drop_index("ix_consolidated_responses_technical_request_id", table_name="consolidated_responses")
    op.drop_table("consolidated_responses")
