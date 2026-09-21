import secrets
from datetime import datetime
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import utc_now
from app.models import OrchestrationEvent, OrchestrationRun, RequestAttachment, TechnicalRequest, User
from app.schemas.orchestration import TechnicalRequestCreate

CONTEXT_MIN_LENGTH = 40


class RequestStatus:
    RECEIVED = "RECEIVED"
    AWAITING_CONTEXT = "AWAITING_CONTEXT"
    QUALIFIED = "QUALIFIED"
    PLANNING = "PLANNING"
    RUNNING = "RUNNING"
    VALIDATING = "VALIDATING"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


ACTIVE_STATUSES = {
    RequestStatus.QUALIFIED,
    RequestStatus.PLANNING,
    RequestStatus.RUNNING,
    RequestStatus.VALIDATING,
}


def generate_trace_id(now: datetime | None = None) -> str:
    instant = now or utc_now()
    return f"TRC-{instant:%Y%m%d}-{secrets.token_hex(3).upper()}"


def has_sufficient_context(context: str | None) -> bool:
    return bool(context and len(context.strip()) >= CONTEXT_MIN_LENGTH)


def append_event(
    db: Session,
    technical_request: TechnicalRequest,
    *,
    event_type: str,
    actor: str,
    title: str,
    message: str,
    payload: dict | None = None,
) -> OrchestrationEvent:
    last_sequence = db.scalar(
        select(func.max(OrchestrationEvent.sequence_number)).where(
            OrchestrationEvent.technical_request_id == technical_request.id
        )
    ) or 0

    event = OrchestrationEvent(
        technical_request_id=technical_request.id,
        orchestration_run_id=(
            technical_request.orchestration_run.id if technical_request.orchestration_run else None
        ),
        sequence_number=last_sequence + 1,
        event_type=event_type,
        actor=actor,
        title=title,
        message=message,
        payload=payload or {},
    )
    db.add(event)
    db.flush()
    return event


def create_technical_request(
    db: Session,
    *,
    owner_id: str,
    input_data: TechnicalRequestCreate,
) -> TechnicalRequest:
    status = (
        RequestStatus.QUALIFIED
        if has_sufficient_context(input_data.context)
        else RequestStatus.AWAITING_CONTEXT
    )

    technical_request = TechnicalRequest(
        owner_id=owner_id,
        trace_id=generate_trace_id(),
        title=input_data.title,
        problem=input_data.problem,
        objective=input_data.objective,
        context=input_data.context,
        restrictions=input_data.restrictions,
        requested_domains=input_data.requested_domains,
        status=status,
    )
    db.add(technical_request)
    db.flush()

    run = OrchestrationRun(
        technical_request_id=technical_request.id,
        status=status,
        current_stage="CONTEXT_QUALIFICATION",
    )
    db.add(run)
    db.flush()
    technical_request.orchestration_run = run

    append_event(
        db,
        technical_request,
        event_type="REQUEST_CREATED",
        actor="USER",
        title="Solicitação registrada",
        message="A solicitação técnica foi registrada e recebeu um Trace ID.",
        payload={"status": RequestStatus.RECEIVED},
    )

    if status == RequestStatus.QUALIFIED:
        append_event(
            db,
            technical_request,
            event_type="CONTEXT_QUALIFIED",
            actor="INTERACTION_GUIDE",
            title="Contexto qualificado",
            message="O contexto mínimo foi identificado. A solicitação está pronta para o planejamento.",
            payload={"next_status": RequestStatus.QUALIFIED},
        )
    else:
        append_event(
            db,
            technical_request,
            event_type="CONTEXT_REQUESTED",
            actor="INTERACTION_GUIDE",
            title="Complementação necessária",
            message=(
                "O contexto inicial ainda é insuficiente. Informe detalhes técnicos, artefatos, "
                "dependências ou comportamento esperado."
            ),
            payload={"minimum_context_characters": CONTEXT_MIN_LENGTH},
        )

    db.flush()
    return technical_request


class RequestNotAwaitingReviewError(ValueError):
    pass


class AttachmentRejectedError(ValueError):
    """Raised for any reason an uploaded document can't become a
    RequestAttachment -- disallowed extension, over the size cap, or bytes
    that don't decode as UTF-8 text. The message is safe to return to the
    caller as-is (no internals leak through it)."""


def record_human_review(
    db: Session,
    *,
    technical_request: TechnicalRequest,
    reviewer: User,
    decision: str,
    notes: str | None = None,
) -> TechnicalRequest:
    """Applies a REVIEWER/ADMIN decision to a request pending human review (RF11,
    RFC §5.3 "Validação": aprovação ou rejeição com justificativa).

    Only requests the Quality Gate actually flagged (status VALIDATING) can be
    reviewed — this is the "humano no loop" checkpoint, not a way to short-circuit
    the automated pipeline before it runs.
    """
    if technical_request.status != RequestStatus.VALIDATING:
        raise RequestNotAwaitingReviewError(
            f"A solicitação está em status '{technical_request.status}' e não aguarda revisão humana."
        )

    approved = decision == "approve"
    next_status = RequestStatus.COMPLETED if approved else RequestStatus.REJECTED
    technical_request.status = next_status

    run = technical_request.orchestration_run
    if run:
        run.status = next_status
        run.current_stage = "VALIDATION"
        run.completed_at = utc_now()

    append_event(
        db,
        technical_request,
        event_type="HUMAN_REVIEW_APPROVED" if approved else "HUMAN_REVIEW_REJECTED",
        actor="REVIEWER",
        title=(
            "Solicitação aprovada por revisão humana"
            if approved
            else "Solicitação rejeitada por revisão humana"
        ),
        message=notes or (
            "Aprovada sem observações adicionais." if approved else "Rejeitada sem observações adicionais."
        ),
        payload={"reviewer_id": reviewer.id, "decision": decision, "notes": notes},
    )

    db.flush()
    return technical_request


def complement_context(
    db: Session,
    *,
    technical_request: TechnicalRequest,
    context: str,
) -> TechnicalRequest:
    technical_request.context = context.strip()

    append_event(
        db,
        technical_request,
        event_type="CONTEXT_PROVIDED",
        actor="USER",
        title="Contexto complementado",
        message="O usuário adicionou novas informações à solicitação técnica.",
    )

    qualified = has_sufficient_context(technical_request.context)
    next_status = RequestStatus.QUALIFIED if qualified else RequestStatus.AWAITING_CONTEXT
    technical_request.status = next_status

    if technical_request.orchestration_run:
        technical_request.orchestration_run.status = next_status
        technical_request.orchestration_run.current_stage = "CONTEXT_QUALIFICATION"

    if qualified:
        append_event(
            db,
            technical_request,
            event_type="CONTEXT_QUALIFIED",
            actor="INTERACTION_GUIDE",
            title="Contexto qualificado",
            message="A solicitação foi qualificada e está pronta para o planejamento da orquestração.",
            payload={"next_status": RequestStatus.QUALIFIED},
        )
    else:
        append_event(
            db,
            technical_request,
            event_type="CONTEXT_REQUESTED",
            actor="INTERACTION_GUIDE",
            title="Mais contexto necessário",
            message="As informações adicionadas ainda não atendem ao contexto mínimo do fluxo.",
            payload={"minimum_context_characters": CONTEXT_MIN_LENGTH},
        )

    db.flush()
    return technical_request


def add_attachment(
    db: Session,
    *,
    technical_request: TechnicalRequest,
    uploaded_by: User,
    filename: str,
    content_type: str | None,
    raw_bytes: bytes,
) -> RequestAttachment:
    """Validates and stores an uploaded document as extra context for a
    request (RFC UX suggestion, PR #24 code review). Deliberately orthogonal
    to complement_context/has_sufficient_context: an attachment never changes
    AWAITING_CONTEXT/QUALIFIED status by itself -- that qualification path is
    specifically about the freeform context field's minimum length, and
    conflating the two would mean a single tiny file could silently qualify
    a request with no real textual context. The content still reaches the
    planner prompt regardless of status (see llm_service._build_safe_request),
    so it isn't ignored -- it just isn't a second route to "qualified"."""
    extension = Path(filename).suffix.lower()
    if not extension or extension not in settings.attachment_allowed_extension_list:
        raise AttachmentRejectedError(
            f"Tipo de arquivo não suportado. Extensões aceitas: "
            f"{', '.join(settings.attachment_allowed_extension_list)}."
        )

    if len(raw_bytes) == 0:
        raise AttachmentRejectedError("O arquivo enviado está vazio.")
    if len(raw_bytes) > settings.attachment_max_bytes:
        raise AttachmentRejectedError(
            f"O arquivo excede o tamanho máximo permitido de "
            f"{settings.attachment_max_bytes // 1000} KB."
        )

    try:
        content = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise AttachmentRejectedError(
            "O arquivo precisa ser texto puro em UTF-8 (documentos binários como "
            "PDF/DOCX ainda não são suportados)."
        ) from exc

    attachment = RequestAttachment(
        technical_request_id=technical_request.id,
        uploaded_by_id=uploaded_by.id,
        filename=filename,
        content_type=content_type,
        content=content,
        size_bytes=len(raw_bytes),
    )
    db.add(attachment)

    append_event(
        db,
        technical_request,
        event_type="ATTACHMENT_ADDED",
        actor="USER",
        title="Documento anexado",
        message=f'O usuário anexou "{filename}" como contexto adicional da solicitação.',
        payload={"filename": filename, "size_bytes": len(raw_bytes)},
    )

    db.flush()
    return attachment


def remove_attachment(
    db: Session,
    *,
    technical_request: TechnicalRequest,
    attachment: RequestAttachment,
) -> None:
    append_event(
        db,
        technical_request,
        event_type="ATTACHMENT_REMOVED",
        actor="USER",
        title="Anexo removido",
        message=f'O usuário removeu o anexo "{attachment.filename}".',
        payload={"filename": attachment.filename},
    )
    db.delete(attachment)
    db.flush()
