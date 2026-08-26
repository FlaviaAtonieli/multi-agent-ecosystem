"""Add RAG knowledge base and retrieval traceability.

Revision ID: 0004_rag_foundation
Revises: 0003_llm_foundation
Create Date: 2026-08-11
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0004_rag_foundation"
down_revision: str | None = "0003_llm_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "knowledge_chunks",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("artifact_name", sa.String(length=200), nullable=False),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("language", sa.String(length=40), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", sa.JSON(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("char_start", sa.Integer(), nullable=False),
        sa.Column("char_end", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_knowledge_chunks_artifact_name", "knowledge_chunks", ["artifact_name"])
    op.create_index("ix_knowledge_chunks_source_type", "knowledge_chunks", ["source_type"])

    op.add_column("llm_invocations", sa.Column("retrieved_chunk_ids", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("llm_invocations", "retrieved_chunk_ids")

    op.drop_index("ix_knowledge_chunks_source_type", table_name="knowledge_chunks")
    op.drop_index("ix_knowledge_chunks_artifact_name", table_name="knowledge_chunks")
    op.drop_table("knowledge_chunks")
