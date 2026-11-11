"""Confere a migração 0019 em PostgreSQL, com dados da versão anterior.

A suíte de testes usa SQLite e cria as tabelas pelos modelos, então não passa pelas
migrações. O CI roda este script contra um PostgreSQL de verdade, com o banco vazio
indicado por DATABASE_URL:

    cd backend && python scripts/check_clan_migration.py
"""

import sys
from pathlib import Path
from uuid import uuid4

from alembic.config import Config
from sqlalchemy import create_engine, text

from alembic import command

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from app.core.config import settings  # noqa: E402

OLD_REVISION = "0018_password_reset"
NEW_REVISION = "0019_clan_skills"


def _insert_skill(
    connection, *, owner_id: str | None, submitted_by: str, domain: str, visibility: str, clan_id=None
):
    skill_id = str(uuid4())
    connection.execute(
        text(
            "INSERT INTO agent_skills (id, name, version, domain, status, enabled, author_origin, "
            "objective, "
            "manifest_json, input_contract_ref, output_contract_ref, uses_external_services, "
            "submitted_by_id, "
            "owner_id, visibility, clan_id) VALUES (:id, :name, '1.0', :domain, 'approved', true, 'Teste', "
            "'Objetivo', '{}', 'entrada', 'saida', false, :submitted_by, :owner_id, :visibility, :clan_id)"
        ),
        {
            "id": skill_id,
            "name": f"Skill {skill_id}",
            "domain": domain,
            "submitted_by": submitted_by,
            "owner_id": owner_id,
            "visibility": visibility,
            "clan_id": clan_id,
        },
    )
    return skill_id


def main() -> None:
    config = Config(str(BACKEND / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND / "alembic"))
    engine = create_engine(settings.database_url)

    command.upgrade(config, OLD_REVISION)

    admin_id, other_id, clan_id = str(uuid4()), str(uuid4()), str(uuid4())
    with engine.begin() as connection:
        for user_id, email in [(admin_id, "admin@example.com"), (other_id, "outra@example.com")]:
            connection.execute(
                text(
                    "INSERT INTO users (id, name, email, is_active, failed_login_attempts) "
                    "VALUES (:id, 'Pessoa', :email, true, 0)"
                ),
                {"id": user_id, "email": email},
            )
        connection.execute(
            text("INSERT INTO clans (id, name, created_by_id) VALUES (:id, 'Comitê antigo', :owner)"),
            {"id": clan_id, "owner": other_id},
        )
        core = _insert_skill(
            connection, owner_id=None, submitted_by=admin_id, domain="codigo_legado", visibility="OFFICIAL"
        )
        owned = _insert_skill(
            connection,
            owner_id=admin_id,
            submitted_by=admin_id,
            domain="regras_negocio",
            visibility="OFFICIAL",
        )
        published = _insert_skill(
            connection,
            owner_id=other_id,
            submitted_by=other_id,
            domain="Contabilidade",
            visibility="OFFICIAL",
        )
        in_clan = _insert_skill(
            connection,
            owner_id=other_id,
            submitted_by=other_id,
            domain="Jurídico",
            visibility="CLAN",
            clan_id=clan_id,
        )

    command.upgrade(config, NEW_REVISION)

    with engine.connect() as connection:
        skills_in = lambda name: set(  # noqa: E731
            connection.scalars(
                text(
                    "SELECT cs.agent_skill_id FROM clan_skills cs JOIN clans c ON c.id = cs.clan_id "
                    "WHERE c.name = :name"
                ),
                {"name": name},
            )
        )
        assert skills_in("Comitê antigo") == {in_clan}, "skill CLAN precisa entrar no próprio comitê"
        ecosystem = skills_in("Ecossistema")
        assert ecosystem == {core, owned}, f"Ecossistema só recebe as oficiais do catálogo: {ecosystem}"
        assert published not in ecosystem
        is_open = connection.scalar(text("SELECT is_open FROM clans WHERE name = 'Ecossistema'"))
        assert is_open is True, "Ecossistema precisa ser aberto"

    command.downgrade(config, OLD_REVISION)
    command.upgrade(config, "head")
    command.downgrade(config, NEW_REVISION)
    command.upgrade(config, "head")
    with engine.connect() as connection:
        embedding = connection.scalar(text("SELECT embedding FROM agent_skills LIMIT 1"))
        assert embedding is None, "embedding começa vazio"
    print("Migração 0019 conferida.")


if __name__ == "__main__":
    main()
