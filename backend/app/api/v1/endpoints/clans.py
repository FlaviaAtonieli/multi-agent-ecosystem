from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_authenticated_csrf
from app.core.database import get_db
from app.core.security import normalize_email
from app.models import AuthSession, Clan, User
from app.schemas.clan import ClanCreate, ClanDetailRead, ClanMemberAdd, ClanMemberRead, ClanRead
from app.services.audit_service import record_audit
from app.services.clan_service import (
    ClanNameConflictError,
    ClanNotFoundError,
    NotClanMemberError,
    add_member,
    create_clan,
    get_clan,
    list_clans,
    list_user_clans,
    remove_member,
)

router = APIRouter(prefix="/clans", tags=["Clãs"])


def _to_detail(clan: Clan) -> ClanDetailRead:
    return ClanDetailRead(
        id=clan.id,
        name=clan.name,
        created_by_id=clan.created_by_id,
        created_at=clan.created_at,
        members=[
            ClanMemberRead(
                user_id=m.user_id, name=m.user.name, email=m.user.email, joined_at=m.joined_at
            )
            for m in clan.memberships
        ],
    )


@router.get("", response_model=list[ClanRead])
def list_all_clans(
    mine: bool = Query(False, description="Se true, retorna só os clãs do usuário autenticado."),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list:
    clans = list_user_clans(db, user.id) if mine else list_clans(db)
    return [
        ClanRead(
            id=clan.id,
            name=clan.name,
            created_by_id=clan.created_by_id,
            created_at=clan.created_at,
            member_count=len(clan.memberships),
        )
        for clan in clans
    ]


@router.post("", response_model=ClanDetailRead, status_code=status.HTTP_201_CREATED)
def create_new_clan(
    payload: ClanCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _: AuthSession = Depends(require_authenticated_csrf),
) -> ClanDetailRead:
    try:
        clan = create_clan(db, name=payload.name, created_by=user)
    except ClanNameConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    record_audit(
        db, request, "CLAN_CREATED", user_id=user.id, details={"clan_id": clan.id, "name": clan.name}
    )
    db.commit()
    return _to_detail(get_clan(db, clan.id))


@router.get("/{clan_id}", response_model=ClanDetailRead)
def get_clan_detail(
    clan_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> ClanDetailRead:
    try:
        clan = get_clan(db, clan_id)
    except ClanNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _to_detail(clan)


@router.post("/{clan_id}/members", response_model=ClanDetailRead, status_code=status.HTTP_201_CREATED)
def add_clan_member(
    clan_id: str,
    payload: ClanMemberAdd,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _: AuthSession = Depends(require_authenticated_csrf),
) -> ClanDetailRead:
    target = db.scalar(select(User).where(User.email == normalize_email(str(payload.email))))
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado.")

    try:
        add_member(db, clan_id=clan_id, user_to_add=target, added_by=user)
    except ClanNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except NotClanMemberError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    record_audit(
        db,
        request,
        "CLAN_MEMBER_ADDED",
        user_id=user.id,
        details={"clan_id": clan_id, "added_user_id": target.id},
    )
    db.commit()
    return _to_detail(get_clan(db, clan_id))


@router.delete("/{clan_id}/members/{user_id}", response_model=ClanDetailRead)
def remove_clan_member(
    clan_id: str,
    user_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _: AuthSession = Depends(require_authenticated_csrf),
) -> ClanDetailRead:
    try:
        remove_member(db, clan_id=clan_id, user_id=user_id, removed_by=user)
    except ClanNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except NotClanMemberError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    record_audit(
        db,
        request,
        "CLAN_MEMBER_REMOVED",
        user_id=user.id,
        details={"clan_id": clan_id, "removed_user_id": user_id},
    )
    db.commit()
    return _to_detail(get_clan(db, clan_id))
