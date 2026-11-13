import asyncio
import json
import logging
import time
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agent_catalog.mcp_client import call_skill_tool
from app.agent_catalog.registry import canonical_domain, list_clan_skills
from app.agent_catalog.tool_interface import SkillToolCall, SkillToolResult
from app.core.config import settings
from app.core.metrics import QUALITY_GATE_VERDICTS, SKILL_INVOCATIONS, SKILL_LATENCY
from app.core.security import utc_now
from app.llm.file_request import asks_for_files
from app.llm.security import content_sha256
from app.models import (
    AgentSkill,
    AgentSkillInvocation,
    ConsolidatedResponse,
    SkillArtifact,
    TechnicalRequest,
    User,
)
from app.quality_gate.service import QualityGateVerdict, evaluate
from app.services.artifact_service import check_package, prepare_files
from app.services.clan_service import is_member
from app.services.orchestration_service import RequestStatus, append_event
from app.services.team_context import TeamEntry, build_team_context, is_code_file, writes_code

logger = logging.getLogger(__name__)

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


def build_technical_synthesis(results: list[SkillToolResult]) -> str:
    """Síntese entre as skills feita por regras, como o Quality Gate, sem um segundo LLM
    resumindo os resumos. A execução inicial e as perguntas de acompanhamento usam a
    mesma, e a tela mostra o mesmo formato.
    """
    return (
        " ".join(
            f"[{result.agente_emissor.dominio}] {result.analise_estruturada.resumo_executivo}"
            for result in results
        )
        if results
        else "Nenhuma Agent Skill produziu resposta para consolidação."
    )


def overall_confidence(results: list[SkillToolResult]) -> str:
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
    """Monta a resposta final consolidada, separada da resposta parcial de cada skill."""
    technical_synthesis = build_technical_synthesis(results)

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

    overall_confidence_level = overall_confidence(results)

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


def active_clan_skills(db: Session, technical_request: TechnicalRequest) -> list[AgentSkill]:
    """As skills que podem responder a esta solicitação. Solicitação antiga, sem clã,
    ou de quem saiu do clã depois de criá-la não tem nenhuma."""
    clan_id = technical_request.clan_id
    if clan_id is None or not is_member(db, clan_id=clan_id, user_id=technical_request.owner_id):
        return []
    return list_clan_skills(db, clan_id=clan_id, only_active=True)


def resolve_target_skills(db: Session, technical_request: TechnicalRequest) -> list[AgentSkill]:
    available = active_clan_skills(db, technical_request)
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
    team_context: str | None = None,
) -> tuple[AgentSkillInvocation, SkillToolResult | None]:
    tool_call = SkillToolCall(
        trace_id=technical_request.trace_id,
        technical_request_id=technical_request.id,
        user_id=user.id,
        agent_skill_id=skill.id,
        analises_requeridas=technical_request.requested_domains,
        requested_model=requested_model,
        additional_question=additional_question,
        team_context=team_context,
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


async def invoke_skills(
    db: Session,
    *,
    skills: list[AgentSkill],
    technical_request: TechnicalRequest,
    user: User,
    requested_model: str | None = None,
    additional_question: str | None = None,
    team_context: str | None = None,
) -> tuple[list[AgentSkillInvocation], list[SkillToolResult]]:
    """Roda as skills ao mesmo tempo, até orchestration_max_parallel_skills.

    Dividir a Session é seguro: _invoke_skill só cede o event loop enquanto espera a
    skill, e faz commit antes, então duas corrotinas nunca se cruzam numa operação de
    banco. O resultado segue a ordem de `skills`, não a ordem de término.
    """
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
                team_context=team_context,
            )

    outcomes = await asyncio.gather(*(invoke_limited(skill) for skill in skills))
    invocations = [invocation for invocation, _ in outcomes]
    results = [result for _, result in outcomes if result is not None]
    return invocations, results


def _invocation_files(db: Session, invocation: AgentSkillInvocation) -> list[tuple[str, str]]:
    return [
        (artifact.filename, artifact.content)
        for artifact in db.scalars(
            select(SkillArtifact)
            .where(SkillArtifact.invocation_id == invocation.id)
            .order_by(SkillArtifact.filename)
        )
    ]


def _team_entries(
    db: Session,
    skills: list[AgentSkill],
    invocations: list[AgentSkillInvocation],
    results: list[SkillToolResult],
) -> list[TeamEntry]:
    names = {skill.id: skill.name for skill in skills}
    summaries = {
        result.agente_emissor.nome: result.analise_estruturada.resumo_executivo for result in results
    }
    entries: list[TeamEntry] = []
    for invocation in invocations:
        if invocation.status != "COMPLETED" or invocation.agent_skill_id not in names:
            continue
        name = names[invocation.agent_skill_id]
        entries.append((name, summaries.get(name, ""), _invocation_files(db, invocation)))
    return entries


async def _invoke_in_stages(
    db: Session,
    *,
    skills: list[AgentSkill],
    technical_request: TechnicalRequest,
    user: User,
    requested_model: str | None,
    files_requested: bool,
) -> tuple[list[AgentSkillInvocation], list[SkillToolResult]]:
    """Com pedido de arquivos, quem escreve código roda depois e recebe as entregas
    das outras skills (app/services/team_context.py). Sem pedido de arquivos, ou
    sem as duas turmas, todas rodam juntas como antes."""
    implementers = [skill for skill in skills if writes_code(skill.manifest_json or {})]
    advisors = [skill for skill in skills if skill not in implementers]
    if not files_requested or not implementers or not advisors:
        return await invoke_skills(
            db, skills=skills, technical_request=technical_request, user=user, requested_model=requested_model
        )

    first_invocations, first_results = await invoke_skills(
        db, skills=advisors, technical_request=technical_request, user=user, requested_model=requested_model
    )
    entries = _team_entries(db, advisors, first_invocations, first_results)
    team_context = build_team_context(entries) if entries else None
    append_event(
        db,
        technical_request,
        event_type="TEAM_CONTEXT_SHARED",
        actor="ORCHESTRATOR",
        title="Entregas compartilhadas com quem escreve o código",
        message=(
            f"{len(entries)} entrega(s) de {', '.join(name for name, _, _ in entries) or 'nenhuma skill'} "
            f"seguem para {', '.join(skill.name for skill in implementers)}."
        ),
        payload={
            "advisors": [name for name, _, _ in entries],
            "implementers": [skill.name for skill in implementers],
            "documents": [filename for _, _, files in entries for filename, _ in files],
            "context_chars": len(team_context or ""),
        },
    )
    db.commit()

    second_invocations, second_results = await invoke_skills(
        db,
        skills=implementers,
        technical_request=technical_request,
        user=user,
        requested_model=requested_model,
        team_context=team_context,
    )

    # Com o contexto, o modelo gratuito às vezes devolveu só um plano. Quem não entregou
    # código tenta de novo uma vez, sem o contexto.
    names = {skill.id: skill for skill in implementers}
    without_code = [
        names[invocation.agent_skill_id]
        for invocation in second_invocations
        if invocation.agent_skill_id in names
        and not any(is_code_file(filename) for filename, _ in _invocation_files(db, invocation))
    ]
    if without_code and team_context:
        append_event(
            db,
            technical_request,
            event_type="IMPLEMENTER_RETRIED",
            actor="ORCHESTRATOR",
            title="Nova tentativa sem as entregas do time",
            message=(
                f"{', '.join(skill.name for skill in without_code)} não entregou código com as entregas "
                "do time. Tentando de novo uma vez, só com a solicitação."
            ),
            payload={"implementers": [skill.name for skill in without_code]},
        )
        db.commit()
        retry_invocations, retry_results = await invoke_skills(
            db,
            skills=without_code,
            technical_request=technical_request,
            user=user,
            requested_model=requested_model,
        )
        retried = {skill.name for skill in without_code}
        second_results = [r for r in second_results if r.agente_emissor.nome not in retried] + retry_results
        second_invocations = second_invocations + retry_invocations

    return first_invocations + second_invocations, first_results + second_results


def _package_issues(db: Session, invocations: list[AgentSkillInvocation]) -> list[str]:
    issues: list[str] = []
    for invocation in invocations:
        issues.extend(check_package(_invocation_files(db, invocation)))
    return issues


def stored_any_file(db: Session, invocations: list[AgentSkillInvocation]) -> bool:
    ids = [invocation.id for invocation in invocations]
    if not ids:
        return False
    count = db.scalar(select(func.count(SkillArtifact.id)).where(SkillArtifact.invocation_id.in_(ids)))
    return bool(count)


async def execute_orchestration_step(
    db: Session,
    *,
    technical_request: TechnicalRequest,
    user: User,
    requested_model: str | None = None,
) -> ExecutionResult:
    """Escolhe e roda as Agent Skills de uma solicitação qualificada (RF08, RF09, RF10)
    e consolida as respostas passando pelo Quality Gate (RF11)."""
    skills = resolve_target_skills(db, technical_request)
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

    files_requested = asks_for_files(technical_request.title, technical_request.objective)
    invocations, results = await _invoke_in_stages(
        db,
        skills=skills,
        technical_request=technical_request,
        user=user,
        requested_model=requested_model,
        files_requested=files_requested,
    )

    verdict = evaluate(
        results,
        files_requested=files_requested,
        files_delivered=stored_any_file(db, invocations),
        package_issues=_package_issues(db, invocations),
    )
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
