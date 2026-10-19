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
    with op.batch_alter_table("agent_skills") as batch_op:
        batch_op.add_column(sa.Column("owner_id", sa.String(length=36), nullable=True))
        batch_op.add_column(
            sa.Column("visibility", sa.String(length=20), nullable=False, server_default="OFFICIAL")
        )
        batch_op.add_column(sa.Column("persona_instructions", sa.Text(), nullable=True))
        batch_op.create_index("ix_agent_skills_owner_id", ["owner_id"])
        batch_op.create_index("ix_agent_skills_visibility", ["visibility"])
        batch_op.create_foreign_key(
            "fk_agent_skills_owner_id_users",
            "users",
            ["owner_id"],
            ["id"],
            ondelete="CASCADE",
        )


def downgrade() -> None:
    with op.batch_alter_table("agent_skills") as batch_op:
        batch_op.drop_constraint("fk_agent_skills_owner_id_users", type_="foreignkey")
        batch_op.drop_index("ix_agent_skills_visibility")
        batch_op.drop_index("ix_agent_skills_owner_id")
        batch_op.drop_column("persona_instructions")
        batch_op.drop_column("visibility")
        batch_op.drop_column("owner_id")
