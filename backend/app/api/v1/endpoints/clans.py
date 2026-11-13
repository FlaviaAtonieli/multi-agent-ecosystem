from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent_catalog.registry import (
    add_skill_to_clan,
    find_visible_skill,
    get_clan_skill_link,
    list_clan_skills,
)
from app.api.dependencies import get_current_user, require_authenticated_csrf
from app.core.database import get_db
from app.core.security import normalize_email
from app.models import AuthSession, Clan, ClanRepository, User
from app.schemas.agent_skill import AgentSkillRead
from app.schemas.clan import (
    ClanCreate,
    ClanDetailRead,
    ClanMemberAdd,
    ClanMemberRead,
    ClanRead,
    ClanRepositoryAdd,
    ClanRepositoryRead,
    ClanSettingsUpdate,
    ClanSkillAdd,
)
from app.services.audit_service import record_audit
from app.services.clan_service import (
    ClanNameConflictError,
    ClanNotFoundError,
    ClanPermissionError,
    add_member,
    create_clan,
    ensure_can_change_repositories,
    ensure_can_register_skills,
    get_clan,
    is_member,
    join_clan,
    list_clans,
    list_user_clans,
    remove_member,
    update_clan_settings,
)
from app.services.repository_service import (
    find_repository,
    parse_github_url,
    remove_repository,
    start_indexing_in_background,
)

router = APIRouter(prefix="/clans", tags=["Comitês"])


def _to_detail(clan: Clan) -> ClanDetailRead:
    return ClanDetailRead(
        id=clan.id,
        name=clan.name,
        created_by_id=clan.created_by_id,
        created_at=clan.created_at,
        members=[
            ClanMemberRead(user_id=m.user_id, name=m.user.name, email=m.user.email, joined_at=m.joined_at)
            for m in clan.memberships
        ],
        is_open=clan.is_open,
        skills_policy=clan.skills_policy,
        members_policy=clan.members_policy,
    )


@router.get("", response_model=list[ClanRead])
def list_all_clans(
    mine: bool = Query(False, description="Se true, retorna só os comitês do usuário autenticado."),
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
            is_open=clan.is_open,
            skills_policy=clan.skills_policy,
            members_policy=clan.members_policy,
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
        clan = create_clan(
            db,
            name=payload.name,
            created_by=user,
            is_open=payload.is_open,
            skills_policy=payload.skills_policy,
            members_policy=payload.members_policy,
        )
    except ClanNameConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    record_audit(
        db,
        request,
        "CLAN_CREATED",
        user_id=user.id,
        details={
            "clan_id": clan.id,
            "name": clan.name,
            "is_open": clan.is_open,
            "skills_policy": clan.skills_policy,
            "members_policy": clan.members_policy,
        },
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


@router.patch("/{clan_id}/settings", response_model=ClanDetailRead)
def update_settings(
    clan_id: str,
    payload: ClanSettingsUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _: AuthSession = Depends(require_authenticated_csrf),
) -> ClanDetailRead:
    try:
        update_clan_settings(
            db,
            clan_id=clan_id,
            updated_by=user,
            name=payload.name,
            is_open=payload.is_open,
            skills_policy=payload.skills_policy,
            members_policy=payload.members_policy,
        )
    except ClanNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ClanNameConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ClanPermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    record_audit(
        db,
        request,
        "CLAN_SETTINGS_UPDATED",
        user_id=user.id,
        details={"clan_id": clan_id, **payload.model_dump(exclude_none=True)},
    )
    db.commit()
    return _to_detail(get_clan(db, clan_id))


@router.post("/{clan_id}/join", response_model=ClanDetailRead)
def join(
    clan_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _: AuthSession = Depends(require_authenticated_csrf),
) -> ClanDetailRead:
    try:
        join_clan(db, clan_id=clan_id, user=user)
    except ClanNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ClanPermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    record_audit(db, request, "CLAN_JOINED", user_id=user.id, details={"clan_id": clan_id})
    db.commit()
    return _to_detail(get_clan(db, clan_id))


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
    except ClanPermissionError as exc:
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
    except ClanPermissionError as exc:
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


def _find_clan(db: Session, clan_id: str) -> Clan:
    try:
        return get_clan(db, clan_id)
    except ClanNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


def _ensure_can_change_skills(db: Session, clan: Clan, user: User) -> None:
    try:
        ensure_can_register_skills(db, clan=clan, user=user)
    except ClanPermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get("/{clan_id}/skills", response_model=list[AgentSkillRead])
def list_skills_of_clan(
    clan_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> object:
    clan = _find_clan(db, clan_id)
    # Num comitê aberto, dá para ver as skills antes de decidir entrar.
    if not clan.is_open and not is_member(db, clan_id=clan_id, user_id=user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Só um membro pode ver as Agent Skills de um comitê fechado.",
        )
    return list_clan_skills(db, clan_id=clan_id)


@router.post("/{clan_id}/skills", response_model=AgentSkillRead, status_code=status.HTTP_201_CREATED)
def add_skill(
    clan_id: str,
    payload: ClanSkillAdd,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _: AuthSession = Depends(require_authenticated_csrf),
) -> object:
    clan = _find_clan(db, clan_id)
    _ensure_can_change_skills(db, clan, user)
    # 404, e não 403: não revela que existe uma skill privada de outra pessoa.
    skill = find_visible_skill(db, skill_id=payload.agent_skill_id, viewer_id=user.id)
    if skill is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent Skill não encontrada.")
    if get_clan_skill_link(db, clan_id=clan_id, skill_id=skill.id) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Esta Agent Skill já está no comitê."
        )

    add_skill_to_clan(db, clan_id=clan_id, skill_id=skill.id, added_by_id=user.id)
    record_audit(
        db,
        request,
        "CLAN_SKILL_ADDED",
        user_id=user.id,
        details={"clan_id": clan_id, "agent_skill_id": skill.id},
    )
    db.commit()
    return skill


@router.delete("/{clan_id}/skills/{skill_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_skill(
    clan_id: str,
    skill_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _: AuthSession = Depends(require_authenticated_csrf),
) -> Response:
    clan = _find_clan(db, clan_id)
    _ensure_can_change_skills(db, clan, user)
    link = get_clan_skill_link(db, clan_id=clan_id, skill_id=skill_id)
    if link is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Esta Agent Skill não está no comitê."
        )

    db.delete(link)
    record_audit(
        db,
        request,
        "CLAN_SKILL_REMOVED",
        user_id=user.id,
        details={"clan_id": clan_id, "agent_skill_id": skill_id},
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _ensure_can_see_repositories(db: Session, clan: Clan, user: User) -> None:
    if not clan.is_open and not is_member(db, clan_id=clan.id, user_id=user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Só um membro pode ver os repositórios de um comitê fechado.",
        )


def _ensure_can_change_repositories(db: Session, clan: Clan, user: User) -> None:
    try:
        ensure_can_change_repositories(db, clan=clan, user=user)
    except ClanPermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


def _find_repository(db: Session, clan_id: str, repository_id: str) -> ClanRepository:
    repository = db.get(ClanRepository, repository_id)
    if repository is None or repository.clan_id != clan_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repositório não encontrado.")
    return repository


@router.get("/{clan_id}/repositories", response_model=list[ClanRepositoryRead])
def list_repositories(
    clan_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ClanRepository]:
    clan = _find_clan(db, clan_id)
    _ensure_can_see_repositories(db, clan, user)
    return list(
        db.scalars(
            select(ClanRepository)
            .where(ClanRepository.clan_id == clan_id)
            .order_by(ClanRepository.created_at.asc())
        )
    )


@router.post(
    "/{clan_id}/repositories", response_model=ClanRepositoryRead, status_code=status.HTTP_201_CREATED
)
async def add_repository(
    clan_id: str,
    payload: ClanRepositoryAdd,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _: AuthSession = Depends(require_authenticated_csrf),
) -> ClanRepository:
    clan = _find_clan(db, clan_id)
    _ensure_can_change_repositories(db, clan, user)
    owner, name = parse_github_url(payload.url)
    if find_repository(db, clan_id=clan_id, owner=owner, name=name) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Este repositório já está no comitê."
        )

    repository = ClanRepository(
        clan_id=clan_id, owner=owner, name=name, url=payload.url, status="PENDING", added_by_id=user.id
    )
    db.add(repository)
    db.flush()
    record_audit(
        db,
        request,
        "CLAN_REPOSITORY_ADDED",
        user_id=user.id,
        details={"clan_id": clan_id, "repository_id": repository.id, "url": payload.url},
    )
    db.commit()
    db.refresh(repository)
    start_indexing_in_background(repository.id)
    return repository


@router.post(
    "/{clan_id}/repositories/{repository_id}/reindex",
    response_model=ClanRepositoryRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def reindex_repository(
    clan_id: str,
    repository_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _: AuthSession = Depends(require_authenticated_csrf),
) -> ClanRepository:
    clan = _find_clan(db, clan_id)
    _ensure_can_change_repositories(db, clan, user)
    repository = _find_repository(db, clan_id, repository_id)
    if repository.status in ("PENDING", "INDEXING"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Este repositório já está sendo indexado."
        )
    repository.status = "PENDING"
    repository.error_message = None
    db.commit()
    db.refresh(repository)
    start_indexing_in_background(repository.id)
    return repository


@router.delete("/{clan_id}/repositories/{repository_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_repository(
    clan_id: str,
    repository_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _: AuthSession = Depends(require_authenticated_csrf),
) -> Response:
    clan = _find_clan(db, clan_id)
    _ensure_can_change_repositories(db, clan, user)
    repository = _find_repository(db, clan_id, repository_id)
    if repository.status == "INDEXING":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Espere a indexação terminar para remover o repositório.",
        )
    remove_repository(db, repository)
    record_audit(
        db,
        request,
        "CLAN_REPOSITORY_REMOVED",
        user_id=user.id,
        details={"clan_id": clan_id, "repository_id": repository_id},
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
