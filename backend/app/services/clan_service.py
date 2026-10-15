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


class ClanPermissionError(PermissionError):
    """Raised when the clan's settings (is_open / members_policy /
    skills_policy) don't allow this user to do the action. The clan owner (created_by_id)
    can do everything in it."""

    pass


class NotClanMemberError(ClanPermissionError):
    """Raised when someone who isn't a current member tries
    to manage the clan -- self-service management is scoped to people already
    inside the clan, not to every registered user."""

    pass


def get_clan(db: Session, clan_id: str) -> Clan:
    # populate_existing: a sessão usa expire_on_commit=False, então sem isso um
    # Clan já carregado na mesma request voltaria com a lista de membros antiga.
    clan = db.get(
        Clan,
        clan_id,
        options=[selectinload(Clan.memberships).selectinload(ClanMembership.user)],
        populate_existing=True,
    )
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


def _allowed_by_policy(db: Session, clan: Clan, user: User, policy: str) -> bool:
    if clan.created_by_id == user.id:
        return True
    return policy == "ALL_MEMBERS" and is_member(db, clan_id=clan.id, user_id=user.id)


def ensure_can_register_skills(db: Session, *, clan: Clan, user: User) -> None:
    if not is_member(db, clan_id=clan.id, user_id=user.id):
        raise NotClanMemberError("Só um membro do clã pode registrar uma skill com visibilidade CLAN nele.")
    if not _allowed_by_policy(db, clan, user, clan.skills_policy):
        raise ClanPermissionError("Neste clã, só o dono pode registrar Agent Skills.")


def create_clan(
    db: Session,
    *,
    name: str,
    created_by: User,
    is_open: bool = False,
    skills_policy: str = "ALL_MEMBERS",
    members_policy: str = "ALL_MEMBERS",
) -> Clan:
    clean_name = name.strip()
    existing = db.scalar(select(Clan).where(Clan.name == clean_name))
    if existing is not None:
        raise ClanNameConflictError(clean_name)

    clan = Clan(
        name=clean_name,
        created_by_id=created_by.id,
        is_open=is_open,
        skills_policy=skills_policy,
        members_policy=members_policy,
    )
    db.add(clan)
    db.flush()

    db.add(
        ClanMembership(clan_id=clan.id, user_id=created_by.id, added_by_id=created_by.id, joined_at=utc_now())
    )
    db.flush()
    return clan


def update_clan_settings(
    db: Session,
    *,
    clan_id: str,
    updated_by: User,
    name: str | None = None,
    is_open: bool | None = None,
    skills_policy: str | None = None,
    members_policy: str | None = None,
) -> Clan:
    clan = get_clan(db, clan_id)
    if clan.created_by_id != updated_by.id:
        raise ClanPermissionError("Só o dono do clã pode alterar as configurações.")
    if name is not None and name.strip() != clan.name:
        clean_name = name.strip()
        if db.scalar(select(Clan.id).where(Clan.name == clean_name, Clan.id != clan.id)) is not None:
            raise ClanNameConflictError(clean_name)
        clan.name = clean_name
    if is_open is not None:
        clan.is_open = is_open
    if skills_policy is not None:
        clan.skills_policy = skills_policy
    if members_policy is not None:
        clan.members_policy = members_policy
    db.flush()
    return clan


def _get_membership(db: Session, *, clan_id: str, user_id: str) -> ClanMembership | None:
    return db.scalar(
        select(ClanMembership).where(ClanMembership.clan_id == clan_id, ClanMembership.user_id == user_id)
    )


def join_clan(db: Session, *, clan_id: str, user: User) -> ClanMembership:
    clan = get_clan(db, clan_id)
    existing = _get_membership(db, clan_id=clan_id, user_id=user.id)
    if existing is not None:
        return existing
    if not clan.is_open:
        raise ClanPermissionError(
            "Este clã é fechado: só entra quem for adicionado por um membro autorizado."
        )

    membership = ClanMembership(clan_id=clan_id, user_id=user.id, added_by_id=user.id)
    db.add(membership)
    db.flush()
    return membership


def add_member(db: Session, *, clan_id: str, user_to_add: User, added_by: User) -> ClanMembership:
    clan = get_clan(db, clan_id)  # raises ClanNotFoundError if missing
    if not is_member(db, clan_id=clan_id, user_id=added_by.id):
        raise NotClanMemberError("Só um membro do clã pode adicionar novos membros.")
    if not _allowed_by_policy(db, clan, added_by, clan.members_policy):
        raise ClanPermissionError("Neste clã, só o dono pode adicionar membros.")

    existing = _get_membership(db, clan_id=clan_id, user_id=user_to_add.id)
    if existing is not None:
        return existing

    membership = ClanMembership(clan_id=clan_id, user_id=user_to_add.id, added_by_id=added_by.id)
    db.add(membership)
    db.flush()
    return membership


def remove_member(db: Session, *, clan_id: str, user_id: str, removed_by: User) -> None:
    clan = get_clan(db, clan_id)  # raises ClanNotFoundError if missing
    leaving = user_id == removed_by.id  # sair do clã é sempre permitido
    if not leaving:
        if not is_member(db, clan_id=clan_id, user_id=removed_by.id):
            raise NotClanMemberError("Só um membro do clã pode remover membros.")
        if not _allowed_by_policy(db, clan, removed_by, clan.members_policy):
            raise ClanPermissionError("Neste clã, só o dono pode remover membros.")
        if user_id == clan.created_by_id:
            raise ClanPermissionError("O dono do clã não pode ser removido por outro membro.")

    membership = _get_membership(db, clan_id=clan_id, user_id=user_id)
    if membership is not None:
        db.delete(membership)
        db.flush()
