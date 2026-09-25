"""Add clans and clan_memberships (self-service groups); AgentSkill gains clan_id.

Builds out the CLAN visibility tier planned since migration 0010
(AgentSkill.visibility already accepted OFFICIAL/PRIVATE/CLAN/PUBLIC as free
text, but only OFFICIAL/PRIVATE were ever wired up). A clan is a self-service
group: any authenticated user can create one (becomes a member automatically)
and any current member can add/remove other users -- no approval/invite flow
in this first version, confirmed scope with the project author. A skill with
visibility="CLAN" is visible/executable only to members of its clan_id.

Revision ID: 0013_clans
Revises: 0012_request_attachments
Create Date: 2026-09-25
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0013_clans"
down_revision: str | None = "0012_request_attachments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "clans",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False, unique=True),
        sa.Column(
            "created_by_id",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.create_table(
        "clan_memberships",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "clan_id",
            sa.String(length=36),
            sa.ForeignKey("clans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "added_by_id",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "joined_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("clan_id", "user_id", name="uq_clan_membership"),
    )
    op.create_index("ix_clan_memberships_clan_id", "clan_memberships", ["clan_id"])
    op.create_index("ix_clan_memberships_user_id", "clan_memberships", ["user_id"])

    op.add_column(
        "agent_skills",
        sa.Column(
            "clan_id",
            sa.String(length=36),
            sa.ForeignKey("clans.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_agent_skills_clan_id", "agent_skills", ["clan_id"])


def downgrade() -> None:
    op.drop_index("ix_agent_skills_clan_id", table_name="agent_skills")
    op.drop_column("agent_skills", "clan_id")
    op.drop_index("ix_clan_memberships_user_id", table_name="clan_memberships")
    op.drop_index("ix_clan_memberships_clan_id", table_name="clan_memberships")
    op.drop_table("clan_memberships")
    op.drop_table("clans")
