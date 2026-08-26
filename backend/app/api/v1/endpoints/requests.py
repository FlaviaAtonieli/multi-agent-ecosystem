from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.dependencies import (
    get_current_session,
    require_authenticated_csrf,
    require_reviewer,
)
from app.core.database import get_db
from app.models import AuthSession, TechnicalRequest, User
from app.schemas.orchestration import (
    TechnicalRequestContextUpdate,
    TechnicalRequestCreate,
    TechnicalRequestRead,
    TechnicalRequestReview,
)
from app.services.audit_service import record_audit
from app.services.orchestration_service import (
    RequestNotAwaitingReviewError,
    complement_context,
    create_technical_request,
    record_human_review,
)


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


def find_request_for_review(db: Session, request_id: str) -> TechnicalRequest:
    """A reviewer decides on other users' requests (RF11 human-in-the-loop), so
    lookup here is deliberately not owner-scoped — access is gated by the
    require_reviewer dependency instead, same pattern used for ADMIN in
    agent_skills._find_qualified_request."""
    technical_request = db.scalar(
        select(TechnicalRequest)
        .options(selectinload(TechnicalRequest.orchestration_run))
        .where(TechnicalRequest.id == request_id)
    )
    if technical_request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Solicitação técnica não encontrada.",
        )
    return technical_request


@router.post("/{request_id}/review", response_model=TechnicalRequestRead)
def review_request(
    request_id: str,
    payload: TechnicalRequestReview,
    request: Request,
    db: Session = Depends(get_db),
    reviewer: User = Depends(require_reviewer),
    _: AuthSession = Depends(require_authenticated_csrf),
) -> TechnicalRequest:
    technical_request = find_request_for_review(db, request_id)
    try:
        reviewed = record_human_review(
            db,
            technical_request=technical_request,
            reviewer=reviewer,
            decision=payload.decision,
            notes=payload.notes,
        )
    except RequestNotAwaitingReviewError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    record_audit(
        db,
        request,
        "HUMAN_REVIEW_DECIDED",
        user_id=reviewer.id,
        details={
            "technical_request_id": reviewed.id,
            "trace_id": reviewed.trace_id,
            "decision": payload.decision,
            "status": reviewed.status,
        },
    )
    db.commit()
    return reviewed


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
