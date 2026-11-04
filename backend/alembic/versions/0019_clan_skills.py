"""Clã passa a ser o escopo da orquestração.

Uma skill pode estar em vários clãs (clan_skills), e cada solicitação nova escolhe
o clã que vai responder (technical_requests.clan_id). A coluna fica opcional só por
causa das solicitações antigas: a API exige o clã nas novas.

As skills CLAN já existentes entram no próprio clã, e o clã aberto "Ecossistema"
recebe as skills oficiais do catálogo, para a orquestração continuar disponível.

Revision ID: 0019_clan_skills
Revises: 0018_password_reset
Create Date: 2026-11-04
"""

from collections.abc import Sequence
from uuid import uuid4

from alembic import op
import sqlalchemy as sa


revision: str = "0019_clan_skills"
down_revision: str | None = "0018_password_reset"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ECOSYSTEM_CLAN_NAME = "Ecossistema"
CATALOG_DOMAINS = (
    "codigo_legado",
    "regras_negocio",
    "arquitetura_software",
    "seguranca_informacao",
    "qualidade_testes",
    "observabilidade_monitoramento",
    "performance_escalabilidade",
    "dados_privacidade",
    "infraestrutura_devops",
    "apis_integracoes",
)


def _create_ecosystem_clan(connection: sa.Connection, clan_skills: sa.Table) -> None:
    owner_id = connection.scalar(
        sa.text(
            "SELECT submitted_by_id FROM agent_skills WHERE visibility = 'OFFICIAL' "
            "ORDER BY created_at LIMIT 1"
        )
    )
    name_in_use = connection.scalar(
        sa.text("SELECT id FROM clans WHERE name = :name"), {"name": ECOSYSTEM_CLAN_NAME}
    )
    if owner_id is None or name_in_use is not None:
        return

    clan_id = str(uuid4())
    connection.execute(
        sa.text(
            "INSERT INTO clans (id, name, created_by_id, is_open, skills_policy, members_policy) "
            "VALUES (:id, :name, :owner, :is_open, 'OWNER_ONLY', 'OWNER_ONLY')"
        ),
        {"id": clan_id, "name": ECOSYSTEM_CLAN_NAME, "owner": owner_id, "is_open": True},
    )
    connection.execute(
        sa.text(
            "INSERT INTO clan_memberships (id, clan_id, user_id, added_by_id) "
            "VALUES (:id, :clan, :owner, :owner)"
        ),
        {"id": str(uuid4()), "clan": clan_id, "owner": owner_id},
    )
    # Sem as skills que usuários publicaram: só as do catálogo oficial entram.
    official = connection.execute(
        sa.text(
            "SELECT id FROM agent_skills WHERE visibility = 'OFFICIAL' "
            "AND domain IN :domains AND (owner_id IS NULL OR owner_id = :owner)"
        ).bindparams(sa.bindparam("domains", expanding=True)),
        {"domains": list(CATALOG_DOMAINS), "owner": owner_id},
    ).scalars()
    rows = [
        {"id": str(uuid4()), "clan_id": clan_id, "agent_skill_id": skill_id, "added_by_id": owner_id}
        for skill_id in official
    ]
    if rows:
        connection.execute(clan_skills.insert(), rows)


def upgrade() -> None:
    clan_skills = op.create_table(
        "clan_skills",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "clan_id", sa.String(length=36), sa.ForeignKey("clans.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "agent_skill_id",
            sa.String(length=36),
            sa.ForeignKey("agent_skills.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "added_by_id",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("added_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("clan_id", "agent_skill_id", name="uq_clan_skill"),
    )
    op.create_index("ix_clan_skills_clan_id", "clan_skills", ["clan_id"])
    op.create_index("ix_clan_skills_agent_skill_id", "clan_skills", ["agent_skill_id"])

    op.add_column("technical_requests", sa.Column("clan_id", sa.String(length=36), nullable=True))
    op.create_index("ix_technical_requests_clan_id", "technical_requests", ["clan_id"])
    op.create_foreign_key(
        "fk_technical_requests_clan_id",
        "technical_requests",
        "clans",
        ["clan_id"],
        ["id"],
        ondelete="SET NULL",
    )

    connection = op.get_bind()
    existing = connection.execute(
        sa.text(
            "SELECT id, clan_id, submitted_by_id FROM agent_skills "
            "WHERE visibility = 'CLAN' AND clan_id IS NOT NULL"
        )
    ).all()
    if existing:
        connection.execute(
            clan_skills.insert(),
            [
                {"id": str(uuid4()), "clan_id": clan_id, "agent_skill_id": skill_id, "added_by_id": added_by}
                for skill_id, clan_id, added_by in existing
            ],
        )
    _create_ecosystem_clan(connection, clan_skills)


def downgrade() -> None:
    # O clã "Ecossistema" fica: é um clã comum, e pode já ter membros.
    op.drop_constraint("fk_technical_requests_clan_id", "technical_requests", type_="foreignkey")
    op.drop_index("ix_technical_requests_clan_id", table_name="technical_requests")
    op.drop_column("technical_requests", "clan_id")
    op.drop_index("ix_clan_skills_agent_skill_id", table_name="clan_skills")
    op.drop_index("ix_clan_skills_clan_id", table_name="clan_skills")
    op.drop_table("clan_skills")
