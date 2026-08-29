from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import require_admin, require_authenticated_csrf
from app.core.config import settings
from app.core.database import get_db
from app.models import AuthSession, LLMInvocation, User
from app.schemas.user import AdminUserRead, UserRead, UserRoleUpdate, UserStatusUpdate
from app.services.audit_service import record_audit
from app.services.session_service import revoke_all_sessions

router = APIRouter(prefix="/admin", tags=["Administration"])


def _tokens_used_today_by_user(db: Session) -> dict[str, int]:
    start_of_day = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    usage_rows = db.execute(
        select(
            LLMInvocation.user_id,
            func.sum(LLMInvocation.input_tokens + LLMInvocation.output_tokens),
        )
        .where(
            LLMInvocation.status == "COMPLETED",
            LLMInvocation.created_at >= start_of_day,
        )
        .group_by(LLMInvocation.user_id)
    ).all()
    return {user_id: int(total or 0) for user_id, total in usage_rows}


def _to_admin_user_read(user: User, tokens_used_today: int) -> AdminUserRead:
    return AdminUserRead(
        **UserRead.model_validate(user).model_dump(),
        tokens_used_today=tokens_used_today,
        daily_token_limit_per_user=settings.llm_daily_token_limit_per_user,
    )


@router.get("/users", response_model=list[AdminUserRead])
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[AdminUserRead]:
    users = list(db.scalars(select(User).order_by(User.created_at.desc())))
    usage_by_user = _tokens_used_today_by_user(db)
    return [_to_admin_user_read(user, usage_by_user.get(user.id, 0)) for user in users]


@router.patch("/users/{user_id}/status", response_model=AdminUserRead)
def update_user_status(
    user_id: str,
    payload: UserStatusUpdate,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
    _: AuthSession = Depends(require_authenticated_csrf),
) -> AdminUserRead:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado.")
    if user.id == admin.id and not payload.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O administrador atual não pode desativar a própria conta.",
        )

    user.is_active = payload.is_active
    if not payload.is_active:
        revoke_all_sessions(db, user.id)
    record_audit(
        db,
        request,
        "ADMIN_USER_STATUS_CHANGED",
        user_id=admin.id,
        details={"target_user_id": user.id, "is_active": user.is_active},
    )
    db.commit()
    db.refresh(user)
    return _to_admin_user_read(user, _tokens_used_today_by_user(db).get(user.id, 0))


@router.patch("/users/{user_id}/role", response_model=AdminUserRead)
def update_user_role(
    user_id: str,
    payload: UserRoleUpdate,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
    _: AuthSession = Depends(require_authenticated_csrf),
) -> AdminUserRead:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado.")
    if user.id == admin.id and payload.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O administrador atual não pode remover o próprio perfil administrativo.",
        )

    previous_role = user.role
    user.role = payload.role
    if previous_role != user.role and user.id != admin.id:
        revoke_all_sessions(db, user.id)

    record_audit(
        db,
        request,
        "ADMIN_USER_ROLE_CHANGED",
        user_id=admin.id,
        details={
            "target_user_id": user.id,
            "previous_role": previous_role,
            "new_role": user.role,
            "sessions_revoked": previous_role != user.role and user.id != admin.id,
        },
    )
    db.commit()
    db.refresh(user)
    return _to_admin_user_read(user, _tokens_used_today_by_user(db).get(user.id, 0))
