from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import require_authenticated_csrf, require_technician
from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.llm.schemas import LLMInvocationRead, LLMPlanResponse, LLMStatusRead
from app.models import AuthSession, LLMInvocation, TechnicalRequest, User
from app.services.audit_service import record_audit
from app.services.llm_service import (
    LLMDisabledError,
    LLMInvocationError,
    generate_technical_plan,
)


router = APIRouter(prefix="/llm", tags=["LLM Integration"])


def _find_request(db: Session, *, user: User, request_id: str | None = None, trace_id: str | None = None) -> TechnicalRequest:
    query = select(TechnicalRequest)
    if request_id:
        query = query.where(TechnicalRequest.id == request_id)
    elif trace_id:
        query = query.where(TechnicalRequest.trace_id == trace_id)
    else:
        raise ValueError("request_id ou trace_id é obrigatório")

    if user.role != "ADMIN":
        query = query.where(TechnicalRequest.owner_id == user.id)

    technical_request = db.scalar(query)
    if technical_request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Solicitação não encontrada.")
    return technical_request


def _find_executable_request(db: Session, request_id: str, user: User) -> TechnicalRequest:
    technical_request = _find_request(db, user=user, request_id=request_id)
    if technical_request.status != "QUALIFIED":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A solicitação precisa estar qualificada antes do planejamento por LLM.",
        )
    return technical_request


def _provider_configured() -> bool:
    if settings.llm_provider == "mock":
        return True
    if settings.llm_provider == "openai":
        return bool(settings.openai_api_key_value)
    if settings.llm_provider == "openrouter":
        return bool(settings.openrouter_api_key_value)
    return False


@router.get("/status", response_model=LLMStatusRead)
def llm_status(_: User = Depends(require_technician)) -> LLMStatusRead:
    configured = _provider_configured()
    return LLMStatusRead(
        enabled=settings.llm_enabled,
        provider=settings.llm_provider,
        model=settings.llm_model,
        configured=configured,
        allowed_models=settings.llm_allowed_model_list,
        max_input_chars=settings.llm_max_input_chars,
        max_output_tokens=settings.llm_max_output_tokens,
        requests_per_hour_technician=settings.llm_requests_per_hour_technician,
        store_provider_response=settings.llm_store_provider_response,
        store_result_content=settings.llm_store_result_content,
    )


@router.get("/invocations/{trace_id}", response_model=list[LLMInvocationRead])
def list_invocations(
    trace_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_technician),
) -> list[LLMInvocation]:
    technical_request = _find_request(db, user=user, trace_id=trace_id)
    return list(
        db.scalars(
            select(LLMInvocation)
            .where(LLMInvocation.technical_request_id == technical_request.id)
            .order_by(LLMInvocation.created_at.desc())
        )
    )


@router.post("/requests/{request_id}/plan", response_model=LLMPlanResponse)
def create_plan(
    request_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_technician),
    _: AuthSession = Depends(require_authenticated_csrf),
) -> LLMPlanResponse:
    limiter.check(
        f"llm:user:{user.id}",
        settings.llm_requests_per_hour_technician,
        3600,
    )
    technical_request = _find_executable_request(db, request_id, user)

    try:
        result = generate_technical_plan(
            db,
            technical_request=technical_request,
            user=user,
        )
    except LLMDisabledError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except LLMInvocationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="O provedor não concluiu o planejamento. Use o Trace ID para suporte.",
        ) from exc

    record_audit(
        db,
        request,
        "LLM_TECHNICAL_PLAN_CREATED",
        user_id=user.id,
        details={
            "technical_request_id": technical_request.id,
            "trace_id": technical_request.trace_id,
            "llm_call_id": result.llm_call_id,
            "provider": result.provider,
            "model": result.model,
        },
    )
    db.commit()
    return result
