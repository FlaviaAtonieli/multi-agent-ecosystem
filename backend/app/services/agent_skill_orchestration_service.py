import json
import time
from uuid import uuid4

from sqlalchemy.orm import Session

from app.agent_catalog.mcp_client import SkillServerNotImplementedError, call_skill_tool
from app.agent_catalog.registry import list_active_skills, select_skills_for_domain
from app.agent_catalog.tool_interface import SkillToolCall, SkillToolResult
from app.core.security import utc_now
from app.llm.security import content_sha256
from app.models import AgentSkill, AgentSkillInvocation, ConsolidatedResponse, TechnicalRequest, User
from app.quality_gate.service import QualityGateVerdict, evaluate
from app.services.orchestration_service import RequestStatus, append_event

_CONFIDENCE_RANK = {"BAIXO": 0, "MEDIO": 1, "ALTO": 2}


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
    consolidada"). Rule-based, mirroring the Quality Gate's own explicit,
    explainable approach — no second LLM pass to summarize the summaries.
    """
    technical_synthesis = (
        " ".join(
            f"[{result.agente_emissor.dominio}] {result.analise_estruturada.resumo_executivo}"
            for result in results
        )
        if results
        else "Nenhuma Agent Skill produziu resposta para consolidação."
    )

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

    overall_confidence_level = min(
        (result.governanca.nivel_confianca for result in results),
        key=lambda level: _CONFIDENCE_RANK[level],
        default="BAIXO",
    )

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


def _resolve_target_skills(db: Session, technical_request: TechnicalRequest) -> list[AgentSkill]:
    domains = technical_request.requested_domains or [
        skill.domain for skill in list_active_skills(db)
    ]
    seen_ids: set[str] = set()
    skills: list[AgentSkill] = []
    for domain in dict.fromkeys(domains):  # de-dupe, preserve order
        for skill in select_skills_for_domain(db, domain=domain):
            if skill.id not in seen_ids:
                seen_ids.add(skill.id)
                skills.append(skill)
    return skills


async def _invoke_skill(
    db: Session,
    *,
    skill: AgentSkill,
    technical_request: TechnicalRequest,
    user: User,
    requested_model: str | None = None,
) -> tuple[AgentSkillInvocation, SkillToolResult | None]:
    tool_call = SkillToolCall(
        trace_id=technical_request.trace_id,
        technical_request_id=technical_request.id,
        user_id=user.id,
        agent_skill_id=skill.id,
        analises_requeridas=technical_request.requested_domains,
        requested_model=requested_model,
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
        result = await call_skill_tool(skill.domain, tool_call)
        latency_ms = round((time.perf_counter() - started) * 1000)

        invocation.status = "COMPLETED"
        invocation.output_hash = content_sha256(result.model_dump_json())
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
            },
        )
        db.commit()
        return invocation, result
    except SkillServerNotImplementedError:
        latency_ms = round((time.perf_counter() - started) * 1000)
        invocation.status = "FAILED"
        invocation.error_code = "EXECUTOR_NOT_IMPLEMENTED"
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

    invocations: list[AgentSkillInvocation] = []
    results: list[SkillToolResult] = []
    for skill in skills:
        invocation, result = await _invoke_skill(
            db, skill=skill, technical_request=technical_request, user=user, requested_model=requested_model
        )
        invocations.append(invocation)
        if result is not None:
            results.append(result)

    verdict = evaluate(results)
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
