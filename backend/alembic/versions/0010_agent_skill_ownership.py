"""Add owner_id, visibility and persona_instructions to agent_skills.

Fase 1 da "rede de agentes": skills passam a poder ser criadas por qualquer
usuario tecnico, nao so pelo catalogo oficial. Toda linha existente (as 4
skills oficiais) recebe visibility='OFFICIAL' via server_default, owner_id
permanece NULL -- nenhuma mudanca de comportamento observavel para o
catalogo atual.

Revision ID: 0010_agent_skill_ownership
Revises: 0009_follow_up_exchanges
Create Date: 2026-09-08
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0010_agent_skill_ownership"
down_revision: str | None = "0009_follow_up_exchanges"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "agent_skills",
        sa.Column("owner_id", sa.String(length=36), nullable=True),
    )
    op.add_column(
        "agent_skills",
        sa.Column(
            "visibility", sa.String(length=20), nullable=False, server_default="OFFICIAL"
        ),
    )
    op.add_column(
        "agent_skills",
        sa.Column("persona_instructions", sa.Text(), nullable=True),
    )
    op.create_index("ix_agent_skills_owner_id", "agent_skills", ["owner_id"])
    op.create_index("ix_agent_skills_visibility", "agent_skills", ["visibility"])
    op.create_foreign_key(
        "fk_agent_skills_owner_id_users",
        "agent_skills",
        "users",
        ["owner_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("fk_agent_skills_owner_id_users", "agent_skills", type_="foreignkey")
    op.drop_index("ix_agent_skills_visibility", table_name="agent_skills")
    op.drop_index("ix_agent_skills_owner_id", table_name="agent_skills")
    op.drop_column("agent_skills", "persona_instructions")
    op.drop_column("agent_skills", "visibility")
    op.drop_column("agent_skills", "owner_id")
