from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.security import utc_now
from app.models import Clan, ClanMembership, User


class ClanNotFoundError(LookupError):
    pass


class ClanNameConflictError(ValueError):
    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Já existe um clã chamado '{name}'.")


class NotClanMemberError(PermissionError):
    """Raised when someone who isn't a current member (and isn't ADMIN) tries
    to add/remove members -- self-service management is scoped to people
    already inside the clan, not to every registered user."""

    pass


def get_clan(db: Session, clan_id: str) -> Clan:
    clan = db.get(Clan, clan_id, options=[selectinload(Clan.memberships).selectinload(ClanMembership.user)])
    if clan is None:
        raise ClanNotFoundError(f"Clã '{clan_id}' não encontrado.")
    return clan


def list_clans(db: Session) -> list[Clan]:
    return list(
        db.scalars(
            select(Clan)
            .options(selectinload(Clan.memberships))
            .order_by(Clan.name)
        )
    )


def list_user_clans(db: Session, user_id: str) -> list[Clan]:
    return list(
        db.scalars(
            select(Clan)
            .join(ClanMembership, ClanMembership.clan_id == Clan.id)
            .where(ClanMembership.user_id == user_id)
            .options(selectinload(Clan.memberships))
            .order_by(Clan.name)
        )
    )


def is_member(db: Session, *, clan_id: str, user_id: str) -> bool:
    return (
        db.scalar(
            select(ClanMembership.id).where(
                ClanMembership.clan_id == clan_id, ClanMembership.user_id == user_id
            )
        )
        is not None
    )


def create_clan(db: Session, *, name: str, created_by: User) -> Clan:
    clean_name = name.strip()
    existing = db.scalar(select(Clan).where(Clan.name == clean_name))
    if existing is not None:
        raise ClanNameConflictError(clean_name)

    clan = Clan(name=clean_name, created_by_id=created_by.id)
    db.add(clan)
    db.flush()

    db.add(
        ClanMembership(clan_id=clan.id, user_id=created_by.id, added_by_id=created_by.id, joined_at=utc_now())
    )
    db.flush()
    return clan


def add_member(db: Session, *, clan_id: str, user_to_add: User, added_by: User) -> ClanMembership:
    get_clan(db, clan_id)  # raises ClanNotFoundError if missing
    if added_by.role != "ADMIN" and not is_member(db, clan_id=clan_id, user_id=added_by.id):
        raise NotClanMemberError("Só um membro do clã (ou ADMIN) pode adicionar novos membros.")

    existing = db.scalar(
        select(ClanMembership).where(
            ClanMembership.clan_id == clan_id, ClanMembership.user_id == user_to_add.id
        )
    )
    if existing is not None:
        return existing

    membership = ClanMembership(clan_id=clan_id, user_id=user_to_add.id, added_by_id=added_by.id)
    db.add(membership)
    db.flush()
    return membership


def remove_member(db: Session, *, clan_id: str, user_id: str, removed_by: User) -> None:
    get_clan(db, clan_id)  # raises ClanNotFoundError if missing
    if removed_by.role != "ADMIN" and not is_member(db, clan_id=clan_id, user_id=removed_by.id):
        raise NotClanMemberError("Só um membro do clã (ou ADMIN) pode remover membros.")

    membership = db.scalar(
        select(ClanMembership).where(ClanMembership.clan_id == clan_id, ClanMembership.user_id == user_id)
    )
    if membership is not None:
        db.delete(membership)
        db.flush()
