from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.dependencies import get_current_session, require_authenticated_csrf
from app.core.database import get_db
from app.models import AuthSession, TechnicalRequest
from app.schemas.orchestration import (
    TechnicalRequestContextUpdate,
    TechnicalRequestCreate,
    TechnicalRequestRead,
)
from app.services.audit_service import record_audit
from app.services.orchestration_service import complement_context, create_technical_request


router = APIRouter(prefix="/requests", tags=["Solicitações técnicas"])


def find_owned_request(db: Session, request_id: str, owner_id: str) -> TechnicalRequest:
    technical_request = db.scalar(
        select(TechnicalRequest)
        .options(selectinload(TechnicalRequest.orchestration_run))
        .where(
            TechnicalRequest.id == request_id,
            TechnicalRequest.owner_id == owner_id,
        )
    )
    if technical_request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Solicitação técnica não encontrada.",
        )
    return technical_request


@router.post("", response_model=TechnicalRequestRead, status_code=status.HTTP_201_CREATED)
def create_request(
    payload: TechnicalRequestCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_session: AuthSession = Depends(require_authenticated_csrf),
) -> TechnicalRequest:
    technical_request = create_technical_request(
        db,
        owner_id=current_session.user_id,
        input_data=payload,
    )
    record_audit(
        db,
        request,
        "ORCHESTRATION_REQUEST_CREATED",
        user_id=current_session.user_id,
        details={
            "technical_request_id": technical_request.id,
            "trace_id": technical_request.trace_id,
            "status": technical_request.status,
        },
    )
    db.commit()
    return technical_request


@router.get("", response_model=list[TechnicalRequestRead])
def list_requests(
    db: Session = Depends(get_db),
    current_session: AuthSession = Depends(get_current_session),
) -> list[TechnicalRequest]:
    return list(
        db.scalars(
            select(TechnicalRequest)
            .where(TechnicalRequest.owner_id == current_session.user_id)
            .order_by(TechnicalRequest.created_at.desc())
        )
    )


@router.get("/{request_id}", response_model=TechnicalRequestRead)
def get_request(
    request_id: str,
    db: Session = Depends(get_db),
    current_session: AuthSession = Depends(get_current_session),
) -> TechnicalRequest:
    return find_owned_request(db, request_id, current_session.user_id)


@router.post("/{request_id}/context", response_model=TechnicalRequestRead)
def add_request_context(
    request_id: str,
    payload: TechnicalRequestContextUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_session: AuthSession = Depends(require_authenticated_csrf),
) -> TechnicalRequest:
    technical_request = find_owned_request(db, request_id, current_session.user_id)
    updated = complement_context(db, technical_request=technical_request, context=payload.context)
    record_audit(
        db,
        request,
        "ORCHESTRATION_CONTEXT_UPDATED",
        user_id=current_session.user_id,
        details={
            "technical_request_id": updated.id,
            "trace_id": updated.trace_id,
            "status": updated.status,
        },
    )
    db.commit()
    return updated
