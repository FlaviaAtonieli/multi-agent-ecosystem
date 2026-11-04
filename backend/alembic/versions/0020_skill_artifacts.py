"""Arquivos entregues pelas Agent Skills.

Ficam fora de agent_skill_invocations.result_payload para a consulta dos resultados
não carregar o conteúdo de todos os arquivos.

Revision ID: 0020_skill_artifacts
Revises: 0019_clan_skills
Create Date: 2026-11-04
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0020_skill_artifacts"
down_revision: str | None = "0019_clan_skills"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "skill_artifacts",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "technical_request_id",
            sa.String(length=36),
            sa.ForeignKey("technical_requests.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "invocation_id",
            sa.String(length=36),
            sa.ForeignKey("agent_skill_invocations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_skill_artifacts_technical_request_id", "skill_artifacts", ["technical_request_id"])
    op.create_index("ix_skill_artifacts_invocation_id", "skill_artifacts", ["invocation_id"])


def downgrade() -> None:
    op.drop_index("ix_skill_artifacts_invocation_id", table_name="skill_artifacts")
    op.drop_index("ix_skill_artifacts_technical_request_id", table_name="skill_artifacts")
    op.drop_table("skill_artifacts")
