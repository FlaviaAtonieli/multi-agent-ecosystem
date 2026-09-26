from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.dependencies import (
    get_current_session,
    require_authenticated_csrf,
    require_reviewer,
)
from app.core.config import settings
from app.core.database import get_db
from app.models import AuthSession, RequestAttachment, TechnicalRequest, User
from app.schemas.orchestration import (
    RequestAttachmentRead,
    TechnicalRequestContextUpdate,
    TechnicalRequestCreate,
    TechnicalRequestRead,
    TechnicalRequestReview,
)
from app.services.audit_service import record_audit
from app.services.orchestration_service import (
    AttachmentRejectedError,
    RequestNotAwaitingReviewError,
    add_attachment,
    complement_context,
    create_technical_request,
    record_human_review,
    remove_attachment,
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


@router.post(
    "/{request_id}/attachments",
    response_model=RequestAttachmentRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_request_attachment(
    request_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_session: AuthSession = Depends(require_authenticated_csrf),
    file: UploadFile = File(...),
) -> RequestAttachment:
    technical_request = find_owned_request(db, request_id, current_session.user_id)

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Envie um arquivo com nome."
        )
    # MaxBodySizeMiddleware already caps the whole request; this is a second,
    # tighter check specific to attachments (settings.attachment_max_bytes is
    # meant to be much smaller than MAX_REQUEST_BODY_BYTES -- see the
    # validator in app/core/config.py) so a too-big file gets a clear 422
    # about the attachment itself, not a generic 413 about the request body.
    raw_bytes = await file.read(settings.attachment_max_bytes + 1)

    try:
        attachment = add_attachment(
            db,
            technical_request=technical_request,
            uploaded_by=current_session.user,
            filename=file.filename,
            content_type=file.content_type,
            raw_bytes=raw_bytes,
        )
    except AttachmentRejectedError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    record_audit(
        db,
        request,
        "REQUEST_ATTACHMENT_ADDED",
        user_id=current_session.user_id,
        details={
            "technical_request_id": technical_request.id,
            "trace_id": technical_request.trace_id,
            "attachment_id": attachment.id,
            "filename": attachment.filename,
            "size_bytes": attachment.size_bytes,
        },
    )
    db.commit()
    return attachment


@router.get("/{request_id}/attachments", response_model=list[RequestAttachmentRead])
def list_request_attachments(
    request_id: str,
    db: Session = Depends(get_db),
    current_session: AuthSession = Depends(get_current_session),
) -> list[RequestAttachment]:
    technical_request = find_owned_request(db, request_id, current_session.user_id)
    return list(technical_request.attachments)


@router.delete("/{request_id}/attachments/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_request_attachment(
    request_id: str,
    attachment_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_session: AuthSession = Depends(require_authenticated_csrf),
) -> Response:
    technical_request = find_owned_request(db, request_id, current_session.user_id)
    attachment = next(
        (item for item in technical_request.attachments if item.id == attachment_id), None
    )
    if attachment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Anexo não encontrado.")

    filename = attachment.filename
    remove_attachment(db, technical_request=technical_request, attachment=attachment)
    record_audit(
        db,
        request,
        "REQUEST_ATTACHMENT_REMOVED",
        user_id=current_session.user_id,
        details={
            "technical_request_id": technical_request.id,
            "trace_id": technical_request.trace_id,
            "attachment_id": attachment_id,
            "filename": filename,
        },
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
