"""Vetor de cada Agent Skill, usado pelo motor de sugestão.

Fica vazio até a primeira sugestão e é gerado de novo quando o texto da skill muda,
o que o hash permite perceber.

Revision ID: 0021_skill_embeddings
Revises: 0020_skill_artifacts
Create Date: 2026-11-04
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0021_skill_embeddings"
down_revision: str | None = "0020_skill_artifacts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("agent_skills", sa.Column("embedding", sa.JSON(), nullable=True))
    op.add_column("agent_skills", sa.Column("embedding_text_hash", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("agent_skills", "embedding_text_hash")
    op.drop_column("agent_skills", "embedding")
