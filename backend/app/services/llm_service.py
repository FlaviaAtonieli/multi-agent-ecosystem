import json
import time
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.roles import ROLE_ADMIN
from app.core.security import utc_now
from app.llm.factory import create_llm_provider
from app.llm.schemas import LLMPlanRequest, LLMPlanResponse
from app.llm.security import content_sha256, sanitize_content
from app.models import LLMInvocation, TechnicalRequest, User
from app.rag.service import retrieve_context_for_request
from app.services.orchestration_service import append_event


class LLMDisabledError(RuntimeError):
    pass


class LLMInvocationError(RuntimeError):
    pass


class LLMModelNotAllowedError(ValueError):
    pass


class LLMQuotaExceededError(RuntimeError):
    pass


def tokens_used_today(db: Session, user_id: str) -> int:
    start_of_day = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    used = db.scalar(
        select(
            func.coalesce(
                func.sum(LLMInvocation.input_tokens + LLMInvocation.output_tokens), 0
            )
        ).where(
            LLMInvocation.user_id == user_id,
            LLMInvocation.status == "COMPLETED",
            LLMInvocation.created_at >= start_of_day,
        )
    )
    return int(used or 0)


def _build_safe_request(
    technical_request: TechnicalRequest,
    *,
    analysis_domain_label: str | None = None,
) -> tuple[LLMPlanRequest, int, bool, str]:
    remaining = settings.llm_max_input_chars
    redacted_count = 0
    any_truncated = False

    def clean(value: str | None) -> str | None:
        nonlocal remaining, redacted_count, any_truncated
        if value is None:
            return None
        if remaining <= 0:
            any_truncated = True
            return ""
        sanitized = sanitize_content(
            value,
            max_chars=remaining,
            redact=settings.llm_redact_sensitive_data,
        )
        redacted_count += sanitized.redacted_fields_count
        any_truncated = any_truncated or sanitized.truncated
        remaining -= len(sanitized.value)
        return sanitized.value

    restrictions: list[str] = []
    for restriction in technical_request.restrictions:
        cleaned = clean(restriction)
        if cleaned:
            restrictions.append(cleaned)

    safe_request = LLMPlanRequest(
        technical_request_id=technical_request.id,
        trace_id=technical_request.trace_id,
        title=clean(technical_request.title) or "Solicitação técnica",
        problem=clean(technical_request.problem) or "Problema não informado",
        objective=clean(technical_request.objective) or "Objetivo não informado",
        context=clean(technical_request.context),
        restrictions=restrictions,
        analysis_domain_label=analysis_domain_label,
    )
    safe_serialized = json.dumps(
        safe_request.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
    )
    return (
        safe_request,
        redacted_count,
        any_truncated,
        content_sha256(safe_serialized),
    )


def generate_technical_plan(
    db: Session,
    *,
    technical_request: TechnicalRequest,
    user: User,
    requested_model: str | None = None,
    analysis_domain_label: str | None = None,
) -> LLMPlanResponse:
    if not settings.llm_enabled:
        raise LLMDisabledError("A integração com LLM está desabilitada pelo administrador.")

    if requested_model and requested_model not in settings.llm_allowed_model_list:
        raise LLMModelNotAllowedError(
            f"O modelo '{requested_model}' não está em LLM_ALLOWED_MODELS."
        )
    resolved_model = requested_model or settings.llm_model

    if user.role != ROLE_ADMIN and settings.llm_daily_token_limit_per_user > 0:
        used = tokens_used_today(db, user.id)
        if used >= settings.llm_daily_token_limit_per_user:
            raise LLMQuotaExceededError(
                f"Limite diário de {settings.llm_daily_token_limit_per_user} tokens por "
                f"usuário atingido ({used} usados hoje). Tente novamente amanhã."
            )

    safe_request, redacted_count, truncated, input_hash = _build_safe_request(
        technical_request, analysis_domain_label=analysis_domain_label
    )

    rag_context = retrieve_context_for_request(db, technical_request, safe_request)
    safe_request.retrieved_context = rag_context.as_prompt_block()
    retrieved_chunk_ids = [chunk.chunk_id for chunk in rag_context.chunks]
    append_event(
        db,
        technical_request,
        event_type="RAG_RETRIEVAL_COMPLETED",
        actor="RETRIEVAL_AGENT",
        title="Recuperação de contexto concluída",
        message="Trechos da base de conhecimento foram recuperados para compor o prompt.",
        payload={
            "chunks_retrieved": len(rag_context.chunks),
            "top_k": settings.rag_top_k,
            "retrieval_latency_ms": rag_context.retrieval_latency_ms,
            "chunk_ids": retrieved_chunk_ids,
        },
    )

    provider = create_llm_provider(settings)
    llm_call_id = str(uuid4())

    invocation = LLMInvocation(
        technical_request_id=technical_request.id,
        orchestration_run_id=(
            technical_request.orchestration_run.id
            if technical_request.orchestration_run
            else None
        ),
        user_id=user.id,
        trace_id=technical_request.trace_id,
        llm_call_id=llm_call_id,
        provider=provider.name,
        model=resolved_model,
        purpose="TECHNICAL_PLANNING",
        prompt_template_id="technical-planner",
        prompt_template_version="v1",
        input_hash=input_hash,
        status="STARTED",
        redacted_fields_count=redacted_count,
        input_truncated=truncated,
        retrieved_chunk_ids=retrieved_chunk_ids or None,
    )
    db.add(invocation)
    append_event(
        db,
        technical_request,
        event_type="LLM_INVOCATION_STARTED",
        actor="TECHNICAL_PLANNER",
        title="Planejamento por modelo iniciado",
        message="Uma chamada rastreável foi iniciada sem execução automática de tools.",
        payload={
            "llm_call_id": llm_call_id,
            "provider": provider.name,
            "model": resolved_model,
            "prompt_template": "technical-planner.v1",
        },
    )
    db.commit()

    started = time.perf_counter()
    try:
        provider_result = provider.generate_plan(safe_request, llm_call_id=llm_call_id, model=resolved_model)
        latency_ms = round((time.perf_counter() - started) * 1000)
        completed_at = utc_now()
        serialized_plan = provider_result.plan.model_dump_json()

        invocation.output_hash = content_sha256(serialized_plan)
        invocation.provider_response_id = provider_result.provider_response_id
        invocation.provider_request_id = provider_result.provider_request_id
        invocation.input_tokens = provider_result.usage.input_tokens
        invocation.output_tokens = provider_result.usage.output_tokens
        invocation.latency_ms = latency_ms
        invocation.status = "COMPLETED"
        invocation.completed_at = completed_at
        if settings.llm_store_result_content:
            invocation.result_payload = provider_result.plan.model_dump(mode="json")

        append_event(
            db,
            technical_request,
            event_type="LLM_INVOCATION_COMPLETED",
            actor="TECHNICAL_PLANNER",
            title="Plano técnico gerado",
            message="A resposta estruturada foi validada e encaminhada para revisão humana.",
            payload={
                "llm_call_id": llm_call_id,
                "latency_ms": latency_ms,
                "input_tokens": provider_result.usage.input_tokens,
                "output_tokens": provider_result.usage.output_tokens,
                "status": "SUCCESS",
                "requires_human_approval": True,
            },
        )
        db.commit()

        return LLMPlanResponse(
            technical_request_id=technical_request.id,
            trace_id=technical_request.trace_id,
            llm_call_id=llm_call_id,
            provider=provider.name,
            model=resolved_model,
            plan=provider_result.plan,
            usage=provider_result.usage,
            completed_at=completed_at,
        )
    except Exception as exc:
        latency_ms = round((time.perf_counter() - started) * 1000)
        invocation.status = "FAILED"
        invocation.error_code = "PROVIDER_ERROR"
        invocation.latency_ms = latency_ms
        invocation.completed_at = utc_now()
        append_event(
            db,
            technical_request,
            event_type="LLM_INVOCATION_FAILED",
            actor="TECHNICAL_PLANNER",
            title="Falha no planejamento por modelo",
            message="A chamada falhou e nenhuma ação automática foi executada.",
            payload={
                "llm_call_id": llm_call_id,
                "error_code": "PROVIDER_ERROR",
                "retryable": True,
            },
        )
        db.commit()
        raise LLMInvocationError("Não foi possível gerar o plano técnico.") from exc
