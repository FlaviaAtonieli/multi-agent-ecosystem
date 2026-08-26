"""Add technical requests and orchestration traceability.

Revision ID: 0002_orchestration
Revises: 0001_auth
Create Date: 2026-07-29
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0002_orchestration"
down_revision: str | None = "0001_auth"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "technical_requests",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("owner_id", sa.String(length=36), nullable=False),
        sa.Column("trace_id", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("problem", sa.Text(), nullable=False),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("context", sa.Text(), nullable=True),
        sa.Column("restrictions", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("trace_id"),
    )
    op.create_index("ix_technical_requests_owner_id", "technical_requests", ["owner_id"], unique=False)
    op.create_index("ix_technical_requests_trace_id", "technical_requests", ["trace_id"], unique=True)
    op.create_index("ix_technical_requests_status", "technical_requests", ["status"], unique=False)

    op.create_table(
        "orchestration_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("technical_request_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("current_stage", sa.String(length=64), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["technical_request_id"], ["technical_requests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("technical_request_id"),
    )
    op.create_index(
        "ix_orchestration_runs_technical_request_id",
        "orchestration_runs",
        ["technical_request_id"],
        unique=True,
    )
    op.create_index("ix_orchestration_runs_status", "orchestration_runs", ["status"], unique=False)

    op.create_table(
        "orchestration_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("technical_request_id", sa.String(length=36), nullable=False),
        sa.Column("orchestration_run_id", sa.String(length=36), nullable=True),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("actor", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["technical_request_id"], ["technical_requests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["orchestration_run_id"], ["orchestration_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "technical_request_id",
            "sequence_number",
            name="uq_orchestration_event_request_sequence",
        ),
    )
    op.create_index(
        "ix_orchestration_events_technical_request_id",
        "orchestration_events",
        ["technical_request_id"],
        unique=False,
    )
    op.create_index(
        "ix_orchestration_events_orchestration_run_id",
        "orchestration_events",
        ["orchestration_run_id"],
        unique=False,
    )
    op.create_index("ix_orchestration_events_event_type", "orchestration_events", ["event_type"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_orchestration_events_event_type", table_name="orchestration_events")
    op.drop_index("ix_orchestration_events_orchestration_run_id", table_name="orchestration_events")
    op.drop_index("ix_orchestration_events_technical_request_id", table_name="orchestration_events")
    op.drop_table("orchestration_events")

    op.drop_index("ix_orchestration_runs_status", table_name="orchestration_runs")
    op.drop_index("ix_orchestration_runs_technical_request_id", table_name="orchestration_runs")
    op.drop_table("orchestration_runs")

    op.drop_index("ix_technical_requests_status", table_name="technical_requests")
    op.drop_index("ix_technical_requests_trace_id", table_name="technical_requests")
    op.drop_index("ix_technical_requests_owner_id", table_name="technical_requests")
    op.drop_table("technical_requests")
