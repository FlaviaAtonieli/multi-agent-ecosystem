"""Add secure LLM invocation traceability.

Revision ID: 0003_llm_foundation
Revises: 0002_orchestration
Create Date: 2026-07-31
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0003_llm_foundation"
down_revision: str | None = "0002_orchestration"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "llm_invocations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("technical_request_id", sa.String(length=36), nullable=False),
        sa.Column("orchestration_run_id", sa.String(length=36), nullable=True),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("trace_id", sa.String(length=40), nullable=False),
        sa.Column("llm_call_id", sa.String(length=36), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("purpose", sa.String(length=80), nullable=False),
        sa.Column("prompt_template_id", sa.String(length=120), nullable=False),
        sa.Column("prompt_template_version", sa.String(length=30), nullable=False),
        sa.Column("input_hash", sa.String(length=64), nullable=False),
        sa.Column("output_hash", sa.String(length=64), nullable=True),
        sa.Column("provider_response_id", sa.String(length=160), nullable=True),
        sa.Column("provider_request_id", sa.String(length=160), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("error_code", sa.String(length=80), nullable=True),
        sa.Column("redacted_fields_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("input_truncated", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("result_payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["orchestration_run_id"], ["orchestration_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["technical_request_id"], ["technical_requests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("llm_call_id"),
    )
    op.create_index("ix_llm_invocations_technical_request_id", "llm_invocations", ["technical_request_id"])
    op.create_index("ix_llm_invocations_orchestration_run_id", "llm_invocations", ["orchestration_run_id"])
    op.create_index("ix_llm_invocations_user_id", "llm_invocations", ["user_id"])
    op.create_index("ix_llm_invocations_trace_id", "llm_invocations", ["trace_id"])
    op.create_index("ix_llm_invocations_llm_call_id", "llm_invocations", ["llm_call_id"], unique=True)
    op.create_index("ix_llm_invocations_status", "llm_invocations", ["status"])


def downgrade() -> None:
    op.drop_index("ix_llm_invocations_status", table_name="llm_invocations")
    op.drop_index("ix_llm_invocations_llm_call_id", table_name="llm_invocations")
    op.drop_index("ix_llm_invocations_trace_id", table_name="llm_invocations")
    op.drop_index("ix_llm_invocations_user_id", table_name="llm_invocations")
    op.drop_index("ix_llm_invocations_orchestration_run_id", table_name="llm_invocations")
    op.drop_index("ix_llm_invocations_technical_request_id", table_name="llm_invocations")
    op.drop_table("llm_invocations")
