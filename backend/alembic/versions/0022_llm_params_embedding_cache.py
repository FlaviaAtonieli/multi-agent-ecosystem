"""Parâmetros de cada chamada ao modelo e cache de embeddings.

temperature e seed ficam em cada invocação para ser possível repetir uma análise com
as mesmas condições. O cache guarda o hash do texto, nunca o texto.

Revision ID: 0022_llm_params_cache
Revises: 0021_skill_embeddings
Create Date: 2026-11-05
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0022_llm_params_cache"
down_revision: str | None = "0021_skill_embeddings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("llm_invocations", sa.Column("temperature", sa.Float(), nullable=True))
    op.add_column("llm_invocations", sa.Column("seed", sa.Integer(), nullable=True))
    op.create_table(
        "embedding_cache",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("text_hash", sa.String(length=64), nullable=False),
        sa.Column("embedding", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("model", "text_hash", name="uq_embedding_cache_model_text"),
    )


def downgrade() -> None:
    op.drop_table("embedding_cache")
    op.drop_column("llm_invocations", "seed")
    op.drop_column("llm_invocations", "temperature")
