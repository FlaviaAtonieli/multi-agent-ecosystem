from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import require_admin, require_authenticated_csrf
from app.core.database import get_db
from app.models import AuthSession, User
from app.schemas.user import UserRead, UserRoleUpdate, UserStatusUpdate
from app.services.audit_service import record_audit
from app.services.session_service import revoke_all_sessions

router = APIRouter(prefix="/admin", tags=["Administration"])


@router.get("/users", response_model=list[UserRead])
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[UserRead]:
    users = list(db.scalars(select(User).order_by(User.created_at.desc())))
    return [UserRead.model_validate(user) for user in users]


@router.patch("/users/{user_id}/status", response_model=UserRead)
def update_user_status(
    user_id: str,
    payload: UserStatusUpdate,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
    _: AuthSession = Depends(require_authenticated_csrf),
) -> UserRead:
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
    return UserRead.model_validate(user)


@router.patch("/users/{user_id}/role", response_model=UserRead)
def update_user_role(
    user_id: str,
    payload: UserRoleUpdate,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
    _: AuthSession = Depends(require_authenticated_csrf),
) -> UserRead:
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
    return UserRead.model_validate(user)
