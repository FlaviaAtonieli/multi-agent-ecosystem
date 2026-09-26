"""Add Agent Skill manifest, catalog and invocation traceability.

Revision ID: 0005_agent_skills
Revises: 0004_rag_foundation
Create Date: 2026-08-11
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0005_agent_skills"
down_revision: str | None = "0004_rag_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "technical_requests",
        sa.Column("requested_domains", sa.JSON(), nullable=False, server_default="[]"),
    )

    op.create_table(
        "agent_skills",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("version", sa.String(length=30), nullable=False),
        sa.Column("domain", sa.String(length=60), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="pending_validation"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("author_origin", sa.String(length=160), nullable=False),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("manifest_markdown", sa.Text(), nullable=True),
        sa.Column("manifest_json", sa.JSON(), nullable=False),
        sa.Column("input_contract_ref", sa.String(length=200), nullable=False),
        sa.Column("output_contract_ref", sa.String(length=200), nullable=False),
        sa.Column("uses_external_services", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("submitted_by_id", sa.String(length=36), nullable=False),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["submitted_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_skills_domain", "agent_skills", ["domain"])
    op.create_index("ix_agent_skills_status", "agent_skills", ["status"])
    op.create_index("ix_agent_skills_submitted_by_id", "agent_skills", ["submitted_by_id"])

    op.create_table(
        "agent_skill_invocations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("technical_request_id", sa.String(length=36), nullable=False),
        sa.Column("orchestration_run_id", sa.String(length=36), nullable=True),
        sa.Column("agent_skill_id", sa.String(length=36), nullable=False),
        sa.Column("trace_id", sa.String(length=40), nullable=False),
        sa.Column("invocation_id", sa.String(length=36), nullable=False),
        sa.Column("input_hash", sa.String(length=64), nullable=False),
        sa.Column("output_hash", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("error_code", sa.String(length=80), nullable=True),
        sa.Column("confidence_level", sa.String(length=10), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("result_payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["technical_request_id"], ["technical_requests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["orchestration_run_id"], ["orchestration_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["agent_skill_id"], ["agent_skills.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("invocation_id"),
    )
    op.create_index("ix_agent_skill_invocations_technical_request_id", "agent_skill_invocations", ["technical_request_id"])
    op.create_index("ix_agent_skill_invocations_orchestration_run_id", "agent_skill_invocations", ["orchestration_run_id"])
    op.create_index("ix_agent_skill_invocations_agent_skill_id", "agent_skill_invocations", ["agent_skill_id"])
    op.create_index("ix_agent_skill_invocations_trace_id", "agent_skill_invocations", ["trace_id"])
    op.create_index("ix_agent_skill_invocations_invocation_id", "agent_skill_invocations", ["invocation_id"], unique=True)
    op.create_index("ix_agent_skill_invocations_status", "agent_skill_invocations", ["status"])


def downgrade() -> None:
    op.drop_index("ix_agent_skill_invocations_status", table_name="agent_skill_invocations")
    op.drop_index("ix_agent_skill_invocations_invocation_id", table_name="agent_skill_invocations")
    op.drop_index("ix_agent_skill_invocations_trace_id", table_name="agent_skill_invocations")
    op.drop_index("ix_agent_skill_invocations_agent_skill_id", table_name="agent_skill_invocations")
    op.drop_index("ix_agent_skill_invocations_orchestration_run_id", table_name="agent_skill_invocations")
    op.drop_index("ix_agent_skill_invocations_technical_request_id", table_name="agent_skill_invocations")
    op.drop_table("agent_skill_invocations")

    op.drop_index("ix_agent_skills_submitted_by_id", table_name="agent_skills")
    op.drop_index("ix_agent_skills_status", table_name="agent_skills")
    op.drop_index("ix_agent_skills_domain", table_name="agent_skills")
    op.drop_table("agent_skills")

    op.drop_column("technical_requests", "requested_domains")
