import asyncio
import json
import logging
import time
from collections.abc import Coroutine
from typing import Any, cast
from uuid import uuid4

from sqlalchemy import CursorResult, func, select, update
from sqlalchemy.orm import Session

from app.agent_catalog.mcp_client import SkillServerNotImplementedError, call_skill_tool
from app.agent_catalog.registry import canonical_domain, list_clan_skills
from app.agent_catalog.tool_interface import SkillToolCall, SkillToolResult
from app.core.config import settings
from app.core.database import SessionLocal
from app.core.metrics import QUALITY_GATE_VERDICTS, SKILL_INVOCATIONS, SKILL_LATENCY
from app.core.security import utc_now
from app.llm.security import content_sha256
from app.models import (
    AgentSkill,
    AgentSkillInvocation,
    ConsolidatedResponse,
    FollowUpExchange,
    OrchestrationEvent,
    SkillArtifact,
    TechnicalRequest,
    User,
)
from app.quality_gate.service import QualityGateVerdict, evaluate
from app.services.artifact_service import prepare_files
from app.services.clan_service import is_member
from app.services.orchestration_service import RequestStatus, append_event

logger = logging.getLogger(__name__)

_CONFIDENCE_RANK = {"BAIXO": 0, "MEDIO": 1, "ALTO": 2}

# asyncio only keeps a weak reference to running tasks: without this set, a
# background orchestration could be garbage-collected halfway through.
_background_tasks: set[asyncio.Task[None]] = set()

_FOLLOW_UP_EVENT_TYPES = ("FOLLOW_UP_QUESTION_ASKED", "FOLLOW_UP_RESPONSE_RECEIVED", "FOLLOW_UP_FAILED")
_NO_FOLLOW_UP_SKILLS_MESSAGE = "Nenhuma Agent Skill ativa disponível para responder a esta pergunta."


class NoAgentSkillsAvailableError(RuntimeError):
    pass


class ExecutionResult:
    def __init__(
        self,
        *,
        results: list[SkillToolResult],
        verdict: QualityGateVerdict,
        invocations: list[AgentSkillInvocation],
        consolidated_response: ConsolidatedResponse,
    ) -> None:
        self.results = results
        self.verdict = verdict
        self.invocations = invocations
        self.consolidated_response = consolidated_response


def _build_technical_synthesis(results: list[SkillToolResult]) -> str:
    """Rule-based cross-agent synthesis, mirroring the Quality Gate's own
    explicit, explainable approach — no second LLM pass to summarize the
    summaries. Shared by the initial consolidation and every follow-up
    exchange, so both render the same domain-tagged shape on the frontend."""
    return (
        " ".join(
            f"[{result.agente_emissor.dominio}] {result.analise_estruturada.resumo_executivo}"
            for result in results
        )
        if results
        else "Nenhuma Agent Skill produziu resposta para consolidação."
    )


def _overall_confidence(results: list[SkillToolResult]) -> str:
    return min(
        (result.governanca.nivel_confianca for result in results),
        key=lambda level: _CONFIDENCE_RANK[level],
        default="BAIXO",
    )


def _consolidate(
    db: Session,
    *,
    technical_request: TechnicalRequest,
    results: list[SkillToolResult],
    verdict: QualityGateVerdict,
    invocations: list[AgentSkillInvocation],
) -> ConsolidatedResponse:
    """Builds the RFC §5.3 "Resposta Final Consolidada": a single synthesized
    answer distinct from each skill's partial response, satisfying RFC §5.5's
    criterion 5 ("diferenciar resposta parcial ... e resposta final
    consolidada").
    """
    technical_synthesis = _build_technical_synthesis(results)

    risks: list[str] = []
    for result in results:
        for risk in result.analise_estruturada.impactos_mapeados:
            if risk not in risks:
                risks.append(risk)

    limitations: list[str] = []
    for result in results:
        if result.governanca.nivel_confianca != "ALTO":
            limitations.append(
                f"{result.agente_emissor.nome} ({result.governanca.nivel_confianca}): "
                f"{result.governanca.justificativa_confianca}"
            )

    recommendations = list(verdict.reasons)
    if verdict.approved and not verdict.requires_human_review:
        recommendations.append("Resposta aprovada pelo Quality Gate; nenhuma ação adicional necessária.")
    else:
        recommendations.append(
            "Revisão humana recomendada antes de aplicar as recomendações desta análise."
        )

    overall_confidence_level = _overall_confidence(results)

    consolidated = technical_request.consolidated_response or ConsolidatedResponse(
        technical_request_id=technical_request.id
    )
    consolidated.trace_id = technical_request.trace_id
    consolidated.technical_synthesis = technical_synthesis
    consolidated.recommendations = recommendations
    consolidated.risks = risks
    consolidated.limitations = limitations
    consolidated.participating_agents = [result.agente_emissor.nome for result in results]
    consolidated.overall_confidence_level = overall_confidence_level
    consolidated.quality_gate_approved = verdict.approved
    consolidated.requires_human_review = verdict.requires_human_review
    consolidated.invocation_ids = [invocation.id for invocation in invocations]

    technical_request.consolidated_response = consolidated
    db.add(consolidated)
    db.flush()
    return consolidated


def _active_clan_skills(db: Session, technical_request: TechnicalRequest) -> list[AgentSkill]:
    """As skills que podem responder a esta solicitação. Solicitação antiga, sem clã,
    ou de quem saiu do clã depois de criá-la não tem nenhuma."""
    clan_id = technical_request.clan_id
    if clan_id is None or not is_member(db, clan_id=clan_id, user_id=technical_request.owner_id):
        return []
    return list_clan_skills(db, clan_id=clan_id, only_active=True)


def _resolve_target_skills(db: Session, technical_request: TechnicalRequest) -> list[AgentSkill]:
    available = _active_clan_skills(db, technical_request)
    if not technical_request.requested_domains:
        return available

    skills: list[AgentSkill] = []
    for domain in dict.fromkeys(technical_request.requested_domains):  # de-dupe, preserve order
        canonical = canonical_domain(db, domain)
        skills.extend(skill for skill in available if skill.domain == canonical)
    return skills


async def _invoke_skill(
    db: Session,
    *,
    skill: AgentSkill,
    technical_request: TechnicalRequest,
    user: User,
    requested_model: str | None = None,
    additional_question: str | None = None,
) -> tuple[AgentSkillInvocation, SkillToolResult | None]:
    tool_call = SkillToolCall(
        trace_id=technical_request.trace_id,
        technical_request_id=technical_request.id,
        user_id=user.id,
        agent_skill_id=skill.id,
        analises_requeridas=technical_request.requested_domains,
        requested_model=requested_model,
        additional_question=additional_question,
    )
    input_hash = content_sha256(tool_call.model_dump_json())
    invocation_id = str(uuid4())

    invocation = AgentSkillInvocation(
        technical_request_id=technical_request.id,
        orchestration_run_id=(
            technical_request.orchestration_run.id if technical_request.orchestration_run else None
        ),
        agent_skill_id=skill.id,
        trace_id=technical_request.trace_id,
        invocation_id=invocation_id,
        input_hash=input_hash,
        status="STARTED",
    )
    db.add(invocation)
    append_event(
        db,
        technical_request,
        event_type="AGENT_SKILL_INVOCATION_STARTED",
        actor="ORCHESTRATOR",
        title=f"Agent Skill acionada: {skill.name}",
        message="A skill foi selecionada para o domínio da solicitação e está em execução.",
        payload={"agent_skill_id": skill.id, "domain": skill.domain, "invocation_id": invocation_id},
    )
    db.commit()

    started = time.perf_counter()

    try:
        result = await call_skill_tool(skill, tool_call)
        latency_ms = round((time.perf_counter() - started) * 1000)

        invocation.status = "COMPLETED"
        invocation.output_hash = content_sha256(result.model_dump_json())
        # O conteúdo fica só em skill_artifacts: daqui em diante, o resultado segue sem ele.
        accepted_files, rejected_files = prepare_files(result.arquivos)
        for file in accepted_files:
            db.add(
                SkillArtifact(
                    technical_request_id=technical_request.id,
                    invocation_id=invocation.id,
                    filename=file.nome,
                    content=file.conteudo,
                    size_bytes=len(file.conteudo.encode("utf-8", errors="replace")),
                )
            )
        result = result.model_copy(update={"arquivos": []})
        SKILL_INVOCATIONS.labels(skill.domain, "COMPLETED").inc()
        SKILL_LATENCY.labels(skill.domain).observe(latency_ms / 1000)
        invocation.confidence_level = result.governanca.nivel_confianca
        invocation.latency_ms = latency_ms
        invocation.completed_at = utc_now()
        invocation.result_payload = result.model_dump(mode="json")
        append_event(
            db,
            technical_request,
            event_type="AGENT_SKILL_INVOCATION_COMPLETED",
            actor="ORCHESTRATOR",
            title=f"Agent Skill concluída: {skill.name}",
            message="A resposta estruturada foi validada contra o contrato de saída (MCP tools/call).",
            payload={
                "agent_skill_id": skill.id,
                "confidence_level": result.governanca.nivel_confianca,
                "latency_ms": latency_ms,
                "artifacts_stored": len(accepted_files),
                "artifacts_rejected": rejected_files,
            },
        )
        db.commit()
        return invocation, result
    except SkillServerNotImplementedError:
        latency_ms = round((time.perf_counter() - started) * 1000)
        invocation.status = "FAILED"
        invocation.error_code = "EXECUTOR_NOT_IMPLEMENTED"
        SKILL_INVOCATIONS.labels(skill.domain, "FAILED").inc()
        invocation.latency_ms = latency_ms
        invocation.completed_at = utc_now()
        append_event(
            db,
            technical_request,
            event_type="AGENT_SKILL_INVOCATION_FAILED",
            actor="ORCHESTRATOR",
            title=f"Agent Skill indisponível: {skill.name}",
            message=f"Não há servidor MCP implementado para o domínio '{skill.domain}' nesta PoC.",
            payload={"agent_skill_id": skill.id, "error_code": "EXECUTOR_NOT_IMPLEMENTED"},
        )
        db.commit()
        return invocation, None
    except Exception as exc:  # noqa: BLE001 - covers SkillMCPError; mirrors llm_service's fail-closed pattern
        latency_ms = round((time.perf_counter() - started) * 1000)
        invocation.status = "FAILED"
        invocation.error_code = "EXECUTOR_ERROR"
        SKILL_INVOCATIONS.labels(skill.domain, "FAILED").inc()
        invocation.latency_ms = latency_ms
        invocation.completed_at = utc_now()
        append_event(
            db,
            technical_request,
            event_type="AGENT_SKILL_INVOCATION_FAILED",
            actor="ORCHESTRATOR",
            title=f"Falha na Agent Skill: {skill.name}",
            message="A execução falhou e nenhuma ação automática foi executada.",
            payload={"agent_skill_id": skill.id, "error_code": "EXECUTOR_ERROR", "detail": str(exc)[:300]},
        )
        db.commit()
        return invocation, None


async def _invoke_skills(
    db: Session,
    *,
    skills: list[AgentSkill],
    technical_request: TechnicalRequest,
    user: User,
    requested_model: str | None = None,
    additional_question: str | None = None,
) -> tuple[list[AgentSkillInvocation], list[SkillToolResult]]:
    """Runs the skills concurrently, up to orchestration_max_parallel_skills.

    Sharing one Session is safe here: _invoke_skill only yields to the event loop
    while awaiting the skill call, and commits before doing so, so no two
    coroutines ever interleave inside a database operation. Results keep the
    order of `skills`, so the consolidated response doesn't depend on which one
    finished first."""
    semaphore = asyncio.Semaphore(settings.orchestration_max_parallel_skills)

    async def invoke_limited(skill: AgentSkill) -> tuple[AgentSkillInvocation, SkillToolResult | None]:
        async with semaphore:
            return await _invoke_skill(
                db,
                skill=skill,
                technical_request=technical_request,
                user=user,
                requested_model=requested_model,
                additional_question=additional_question,
            )

    outcomes = await asyncio.gather(*(invoke_limited(skill) for skill in skills))
    invocations = [invocation for invocation, _ in outcomes]
    results = [result for _, result in outcomes if result is not None]
    return invocations, results


async def execute_orchestration_step(
    db: Session,
    *,
    technical_request: TechnicalRequest,
    user: User,
    requested_model: str | None = None,
) -> ExecutionResult:
    """Selects and runs Agent Skills for a qualified request (RF08/RF09/RF10),
    then consolidates their responses through the Quality Gate (RF11)."""
    skills = _resolve_target_skills(db, technical_request)
    if not skills:
        raise NoAgentSkillsAvailableError(
            "Nenhuma Agent Skill ativa e compatível com o domínio da solicitação foi encontrada."
        )

    run = technical_request.orchestration_run
    if run and run.started_at is None:
        run.started_at = utc_now()
    if run:
        run.current_stage = "AGENT_EXECUTION"
        run.status = RequestStatus.RUNNING
        technical_request.status = RequestStatus.RUNNING
        db.commit()

    append_event(
        db,
        technical_request,
        event_type="ORCHESTRATION_EXECUTION_STARTED",
        actor="ORCHESTRATOR",
        title="Execução da orquestração iniciada",
        message=f"{len(skills)} Agent Skill(s) serão consultadas.",
        payload={"total_skills": len(skills), "max_parallel": settings.orchestration_max_parallel_skills},
    )
    for skill in skills:
        append_event(
            db,
            technical_request,
            event_type="AGENT_SKILL_SELECTED",
            actor="ORCHESTRATOR",
            title=f"Agent Skill selecionada: {skill.name}",
            message=f"Selecionada com base no domínio '{skill.domain}' da solicitação.",
            payload={"agent_skill_id": skill.id, "domain": skill.domain},
        )
    db.commit()

    invocations, results = await _invoke_skills(
        db, skills=skills, technical_request=technical_request, user=user, requested_model=requested_model
    )

    verdict = evaluate(results)
    QUALITY_GATE_VERDICTS.labels(
        "approved" if verdict.approved and not verdict.requires_human_review else "human_review"
    ).inc()
    append_event(
        db,
        technical_request,
        event_type="QUALITY_GATE_EVALUATED",
        actor="ADVISORY_AGENT",
        title="Quality Gate avaliado",
        message="; ".join(verdict.reasons) if verdict.reasons else "Avaliação concluída.",
        payload=json.loads(verdict.model_dump_json()),
    )

    if run:
        run.current_stage = "VALIDATION"
        if verdict.approved and not verdict.requires_human_review:
            technical_request.status = RequestStatus.COMPLETED
            run.status = RequestStatus.COMPLETED
            run.completed_at = utc_now()
        else:
            technical_request.status = RequestStatus.VALIDATING
            run.status = RequestStatus.VALIDATING

    consolidated_response = _consolidate(
        db,
        technical_request=technical_request,
        results=results,
        verdict=verdict,
        invocations=invocations,
    )
    append_event(
        db,
        technical_request,
        event_type="RESPONSE_CONSOLIDATED",
        actor="ORCHESTRATOR",
        title="Resposta final consolidada",
        message=(
            f"{len(results)} resposta(s) parcial(is) consolidada(s) em uma síntese única "
            f"(confiança geral: {consolidated_response.overall_confidence_level})."
        ),
        payload={"consolidated_response_id": consolidated_response.id},
    )

    db.commit()
    return ExecutionResult(
        results=results,
        verdict=verdict,
        invocations=invocations,
        consolidated_response=consolidated_response,
    )


def has_target_skills(db: Session, technical_request: TechnicalRequest) -> bool:
    return bool(_resolve_target_skills(db, technical_request))


def claim_request_for_execution(db: Session, technical_request: TechnicalRequest) -> bool:
    """Atomically moves a request to RUNNING, so two clicks on "Executar" can't
    start two runs. FAILED is accepted so an interrupted run can be retried."""
    claimed = cast(
        CursorResult,
        db.execute(
            update(TechnicalRequest)
            .where(
                TechnicalRequest.id == technical_request.id,
                TechnicalRequest.status.in_([RequestStatus.QUALIFIED, RequestStatus.FAILED]),
            )
            .values(status=RequestStatus.RUNNING)
        ),
    )
    if claimed.rowcount != 1:
        db.rollback()
        return False
    db.refresh(technical_request)
    run = technical_request.orchestration_run
    if run:
        run.status = RequestStatus.RUNNING
        run.completed_at = None
    db.commit()
    return True


def _mark_failed(db: Session, technical_request: TechnicalRequest, *, title: str, message: str) -> None:
    technical_request.status = RequestStatus.FAILED
    run = technical_request.orchestration_run
    if run:
        run.status = RequestStatus.FAILED
        run.completed_at = utc_now()
    append_event(
        db,
        technical_request,
        event_type="ORCHESTRATION_EXECUTION_FAILED",
        actor="ORCHESTRATOR",
        title=title,
        message=message,
    )
    db.commit()


async def _run_orchestration(request_id: str, user_id: str, requested_model: str | None) -> None:
    with SessionLocal() as db:
        technical_request = db.get(TechnicalRequest, request_id)
        user = db.get(User, user_id)
        if technical_request is None or user is None:
            logger.error("Orquestração %s não iniciada: solicitação ou usuário não encontrado.", request_id)
            return
        try:
            await execute_orchestration_step(
                db, technical_request=technical_request, user=user, requested_model=requested_model
            )
        except Exception:  # noqa: BLE001 - no caller left to answer: record it on the request instead
            logger.exception("Falha na orquestração em segundo plano %s", technical_request.trace_id)
            db.rollback()
            _mark_failed(
                db,
                technical_request,
                title="Falha na execução da orquestração",
                message="A execução foi interrompida por um erro inesperado. Tente executar novamente.",
            )


def _spawn(coroutine: Coroutine[Any, Any, None]) -> None:
    task = asyncio.create_task(coroutine)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


def start_orchestration_in_background(
    *, request_id: str, user_id: str, requested_model: str | None = None
) -> None:
    """Runs the orchestration detached from the HTTP request: skills can take
    minutes in total, longer than the 45 s the Static Web Apps
    proxy allows a call to /api. The frontend follows progress through the
    request's event timeline."""
    _spawn(_run_orchestration(request_id, user_id, requested_model))


def fail_interrupted_orchestrations(db: Session) -> int:
    """Called on startup. A background run only lives in this process, so any
    request still RUNNING after a restart will never finish on its own. Assumes
    a single worker process (see the CMD in backend/Dockerfile): with several,
    this would also fail runs that are alive in another process."""
    interrupted = list(
        db.scalars(select(TechnicalRequest).where(TechnicalRequest.status == RequestStatus.RUNNING))
    )
    for technical_request in interrupted:
        _mark_failed(
            db,
            technical_request,
            title="Execução interrompida",
            message="O servidor reiniciou durante a execução. Tente executar novamente.",
        )
    return len(interrupted)


async def ask_follow_up_question(
    db: Session,
    *,
    technical_request: TechnicalRequest,
    user: User,
    question: str,
    target_domain: str | None = None,
    requested_model: str | None = None,
) -> FollowUpExchange:
    """Continues the same orchestration chain (trace_id) after the initial
    execution: the user can keep asking questions, either broadcast to every
    domain the original run used (target_domain=None) or aimed at one
    specific Agent Skill domain. Every round — even a single agent answering —
    still goes through the same Quality Gate as the initial execution (RF11),
    and is kept as its own row so the conversation history survives (unlike
    ConsolidatedResponse, one per TechnicalRequest)."""
    skills = _follow_up_skills(db, technical_request, target_domain)
    if not skills:
        raise NoAgentSkillsAvailableError(_NO_FOLLOW_UP_SKILLS_MESSAGE)

    record_follow_up_question(db, technical_request, question=question, target_domain=target_domain)
    return await _answer_follow_up(
        db,
        technical_request=technical_request,
        user=user,
        skills=skills,
        question=question,
        target_domain=target_domain,
        requested_model=requested_model,
    )


def _follow_up_skills(
    db: Session, technical_request: TechnicalRequest, target_domain: str | None
) -> list[AgentSkill]:
    if target_domain:
        canonical = canonical_domain(db, target_domain)
        return [skill for skill in _active_clan_skills(db, technical_request) if skill.domain == canonical]
    return _resolve_target_skills(db, technical_request)


def has_follow_up_skills(
    db: Session, technical_request: TechnicalRequest, target_domain: str | None
) -> bool:
    return bool(_follow_up_skills(db, technical_request, target_domain))


def record_follow_up_question(
    db: Session, technical_request: TechnicalRequest, *, question: str, target_domain: str | None
) -> None:
    append_event(
        db,
        technical_request,
        event_type="FOLLOW_UP_QUESTION_ASKED",
        actor="USER",
        title="Pergunta de acompanhamento registrada",
        message=question,
        payload={"target_domain": target_domain},
    )
    db.commit()


def has_pending_follow_up(db: Session, technical_request: TechnicalRequest) -> bool:
    """The timeline is the source of truth: a question is pending while it is the
    latest follow-up event of the request."""
    latest = db.scalar(
        select(OrchestrationEvent.event_type)
        .where(
            OrchestrationEvent.technical_request_id == technical_request.id,
            OrchestrationEvent.event_type.in_(_FOLLOW_UP_EVENT_TYPES),
        )
        .order_by(OrchestrationEvent.sequence_number.desc())
        .limit(1)
    )
    return latest == "FOLLOW_UP_QUESTION_ASKED"


async def _run_follow_up(
    request_id: str,
    user_id: str,
    question: str,
    target_domain: str | None,
    requested_model: str | None,
) -> None:
    with SessionLocal() as db:
        technical_request = db.get(TechnicalRequest, request_id)
        user = db.get(User, user_id)
        if technical_request is None or user is None:
            logger.error("Pergunta da solicitação %s não respondida: registro não encontrado.", request_id)
            return
        try:
            skills = _follow_up_skills(db, technical_request, target_domain)
            if not skills:
                raise NoAgentSkillsAvailableError(_NO_FOLLOW_UP_SKILLS_MESSAGE)
            await _answer_follow_up(
                db,
                technical_request=technical_request,
                user=user,
                skills=skills,
                question=question,
                target_domain=target_domain,
                requested_model=requested_model,
            )
        except Exception:  # noqa: BLE001 - no caller left to answer: record it on the request instead
            logger.exception("Falha na pergunta em segundo plano %s", technical_request.trace_id)
            db.rollback()
            _record_follow_up_failure(
                db, technical_request, "A pergunta não pôde ser respondida. Tente novamente."
            )


def start_follow_up_in_background(
    *,
    request_id: str,
    user_id: str,
    question: str,
    target_domain: str | None = None,
    requested_model: str | None = None,
) -> None:
    """Same reason as start_orchestration_in_background: several skills can take
    longer than the 45 s limit of the Static Web Apps proxy."""
    _spawn(_run_follow_up(request_id, user_id, question, target_domain, requested_model))


def _record_follow_up_failure(db: Session, technical_request: TechnicalRequest, message: str) -> None:
    append_event(
        db,
        technical_request,
        event_type="FOLLOW_UP_FAILED",
        actor="ORCHESTRATOR",
        title="Falha na pergunta de acompanhamento",
        message=message,
    )
    db.commit()


def fail_interrupted_follow_ups(db: Session) -> int:
    """Same assumption as fail_interrupted_orchestrations: one worker process."""
    request_ids = db.scalars(
        select(OrchestrationEvent.technical_request_id)
        .where(OrchestrationEvent.event_type == "FOLLOW_UP_QUESTION_ASKED")
        .distinct()
    ).all()
    interrupted = 0
    for request_id in request_ids:
        technical_request = db.get(TechnicalRequest, request_id)
        if technical_request is not None and has_pending_follow_up(db, technical_request):
            _record_follow_up_failure(
                db, technical_request, "O servidor reiniciou antes da resposta. Faça a pergunta novamente."
            )
            interrupted += 1
    return interrupted


async def _answer_follow_up(
    db: Session,
    *,
    technical_request: TechnicalRequest,
    user: User,
    skills: list[AgentSkill],
    question: str,
    target_domain: str | None,
    requested_model: str | None,
) -> FollowUpExchange:
    _, results = await _invoke_skills(
        db,
        skills=skills,
        technical_request=technical_request,
        user=user,
        requested_model=requested_model,
        additional_question=question,
    )

    verdict = evaluate(results)
    append_event(
        db,
        technical_request,
        event_type="QUALITY_GATE_EVALUATED",
        actor="ADVISORY_AGENT",
        title="Quality Gate avaliado (pergunta de acompanhamento)",
        message="; ".join(verdict.reasons) if verdict.reasons else "Avaliação concluída.",
        payload=json.loads(verdict.model_dump_json()),
    )

    next_sequence = (
        db.scalar(
            select(func.coalesce(func.max(FollowUpExchange.sequence_number), 0)).where(
                FollowUpExchange.technical_request_id == technical_request.id
            )
        )
        or 0
    ) + 1

    exchange = FollowUpExchange(
        technical_request_id=technical_request.id,
        trace_id=technical_request.trace_id,
        asked_by_id=user.id,
        sequence_number=next_sequence,
        question=question,
        target_domain=target_domain,
        synthesis=_build_technical_synthesis(results),
        results=[result.model_dump(mode="json") for result in results],
        overall_confidence_level=_overall_confidence(results),
        quality_gate_approved=verdict.approved,
        requires_human_review=verdict.requires_human_review,
    )
    db.add(exchange)
    append_event(
        db,
        technical_request,
        event_type="FOLLOW_UP_RESPONSE_RECEIVED",
        actor="ORCHESTRATOR",
        title="Resposta de acompanhamento consolidada",
        message=(
            f"{len(results)} resposta(s) recebida(s) para a pergunta de acompanhamento "
            f"(confiança geral: {exchange.overall_confidence_level})."
        ),
        payload={"target_domain": target_domain, "sequence_number": next_sequence},
    )

    db.commit()
    db.refresh(exchange)
    return exchange
