"""Repositório do GitHub como base de conhecimento do comitê.

Os trechos da base ganham comitê e repositório de origem. Os que já existem ficam
sem comitê, como base global consultada por toda orquestração.

Revision ID: 0024_clan_repositories
Revises: 0023_agent_feedback
Create Date: 2026-11-13
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0024_clan_repositories"
down_revision: str | None = "0023_agent_feedback"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "clan_repositories",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "clan_id", sa.String(length=36), sa.ForeignKey("clans.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("owner", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("url", sa.String(length=300), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("file_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("chunk_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "added_by_id",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("clan_id", "owner", "name", name="uq_clan_repository"),
    )
    op.create_index("ix_clan_repositories_clan_id", "clan_repositories", ["clan_id"])
    op.create_index("ix_clan_repositories_status", "clan_repositories", ["status"])
    op.create_index("ix_clan_repositories_added_by_id", "clan_repositories", ["added_by_id"])

    op.add_column("knowledge_chunks", sa.Column("clan_id", sa.String(length=36), nullable=True))
    op.add_column("knowledge_chunks", sa.Column("repository_id", sa.String(length=36), nullable=True))
    op.create_foreign_key(
        "fk_knowledge_chunks_clan_id", "knowledge_chunks", "clans", ["clan_id"], ["id"], ondelete="CASCADE"
    )
    op.create_foreign_key(
        "fk_knowledge_chunks_repository_id",
        "knowledge_chunks",
        "clan_repositories",
        ["repository_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_knowledge_chunks_clan_id", "knowledge_chunks", ["clan_id"])
    op.create_index("ix_knowledge_chunks_repository_id", "knowledge_chunks", ["repository_id"])


def downgrade() -> None:
    op.drop_index("ix_knowledge_chunks_repository_id", table_name="knowledge_chunks")
    op.drop_index("ix_knowledge_chunks_clan_id", table_name="knowledge_chunks")
    op.drop_constraint("fk_knowledge_chunks_repository_id", "knowledge_chunks", type_="foreignkey")
    op.drop_constraint("fk_knowledge_chunks_clan_id", "knowledge_chunks", type_="foreignkey")
    op.drop_column("knowledge_chunks", "repository_id")
    op.drop_column("knowledge_chunks", "clan_id")
    op.drop_index("ix_clan_repositories_added_by_id", table_name="clan_repositories")
    op.drop_index("ix_clan_repositories_status", table_name="clan_repositories")
    op.drop_index("ix_clan_repositories_clan_id", table_name="clan_repositories")
    op.drop_table("clan_repositories")
