"""Avaliação humana da resposta de cada agente.

Revision ID: 0023_agent_feedback
Revises: 0022_llm_params_cache
Create Date: 2026-11-11
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0023_agent_feedback"
down_revision: str | None = "0022_llm_params_cache"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agent_response_feedback",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "invocation_id",
            sa.String(length=36),
            sa.ForeignKey("agent_skill_invocations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("useful", sa.Boolean(), nullable=False),
        sa.Column("reason", sa.String(length=30), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_agent_response_feedback_invocation_id", "agent_response_feedback", ["invocation_id"], unique=True
    )
    op.create_index("ix_agent_response_feedback_user_id", "agent_response_feedback", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_agent_response_feedback_user_id", table_name="agent_response_feedback")
    op.drop_index("ix_agent_response_feedback_invocation_id", table_name="agent_response_feedback")
    op.drop_table("agent_response_feedback")
