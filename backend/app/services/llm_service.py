import json
import time
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import utc_now
from app.llm.factory import create_llm_provider
from app.llm.schemas import LLMPlanRequest, LLMPlanResponse
from app.llm.security import content_sha256, sanitize_content
from app.models import LLMInvocation, TechnicalRequest, User
from app.services.orchestration_service import append_event


class LLMDisabledError(RuntimeError):
    pass


class LLMInvocationError(RuntimeError):
    pass


def _build_safe_request(
    technical_request: TechnicalRequest,
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
) -> LLMPlanResponse:
    if not settings.llm_enabled:
        raise LLMDisabledError("A integração com LLM está desabilitada pelo administrador.")

    safe_request, redacted_count, truncated, input_hash = _build_safe_request(technical_request)

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
        model=settings.llm_model,
        purpose="TECHNICAL_PLANNING",
        prompt_template_id="technical-planner",
        prompt_template_version="v1",
        input_hash=input_hash,
        status="STARTED",
        redacted_fields_count=redacted_count,
        input_truncated=truncated,
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
            "model": settings.llm_model,
            "prompt_template": "technical-planner.v1",
        },
    )
    db.commit()

    started = time.perf_counter()
    try:
        provider_result = provider.generate_plan(safe_request, llm_call_id=llm_call_id)
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
            model=settings.llm_model,
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
