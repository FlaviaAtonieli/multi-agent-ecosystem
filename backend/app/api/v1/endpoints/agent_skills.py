from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent_catalog.registry import (
    AgentSkillNotFoundError,
    AgentSkillValidationError,
    disable_skill,
    enable_skill,
    get_skill,
    list_active_skills,
    list_all_skills,
    register_skill,
)
from app.agent_catalog.tool_interface import list_tools
from app.agent_manifest.manifest import AgentSkillManifest, ManifestParseError, parse_modelo_md
from app.api.dependencies import (
    get_current_session,
    require_admin,
    require_authenticated_csrf,
    require_technician,
)
from app.core.database import get_db
from app.models import AuthSession, TechnicalRequest, User
from app.schemas.agent_skill import (
    AgentSkillManifestCreate,
    AgentSkillManifestImport,
    AgentSkillRead,
    AgentSkillToolDescriptorRead,
    ConsolidatedResponseRead,
    OrchestrationExecutionRead,
)
from app.services.agent_skill_orchestration_service import (
    NoAgentSkillsAvailableError,
    execute_orchestration_step,
)
from app.services.audit_service import record_audit

router = APIRouter(prefix="/agent-skills", tags=["Agent Skills"])


def _find_qualified_request(db: Session, request_id: str, user: User) -> TechnicalRequest:
    query = select(TechnicalRequest).where(TechnicalRequest.id == request_id)
    if user.role != "ADMIN":
        query = query.where(TechnicalRequest.owner_id == user.id)
    technical_request = db.scalar(query)
    if technical_request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Solicitação não encontrada.")
    if technical_request.status != "QUALIFIED":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A solicitação precisa estar qualificada antes da execução das Agent Skills.",
        )
    return technical_request


@router.get("", response_model=list[AgentSkillRead])
def list_skills(
    only_active: bool = True,
    db: Session = Depends(get_db),
    _: AuthSession = Depends(get_current_session),
) -> list:
    return list_active_skills(db) if only_active else list_all_skills(db)


@router.get("/tools", response_model=list[AgentSkillToolDescriptorRead])
def list_skill_tools(
    db: Session = Depends(get_db),
    _: AuthSession = Depends(get_current_session),
) -> list:
    return list_tools(list_active_skills(db))


@router.post("", response_model=AgentSkillRead, status_code=status.HTTP_201_CREATED)
def create_skill(
    payload: AgentSkillManifestCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_technician),
    _: AuthSession = Depends(require_authenticated_csrf),
) -> object:
    manifest = AgentSkillManifest(**payload.model_dump())
    try:
        skill = register_skill(db, manifest=manifest, submitted_by=user)
    except AgentSkillValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="; ".join(exc.errors)
        ) from exc

    record_audit(
        db,
        request,
        "AGENT_SKILL_REGISTERED",
        user_id=user.id,
        details={"agent_skill_id": skill.id, "domain": skill.domain, "source": "assisted_form"},
    )
    db.commit()
    return skill


@router.post("/import", response_model=AgentSkillRead, status_code=status.HTTP_201_CREATED)
def import_skill(
    payload: AgentSkillManifestImport,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_technician),
    _: AuthSession = Depends(require_authenticated_csrf),
) -> object:
    try:
        manifest = parse_modelo_md(payload.manifest_markdown)
    except ManifestParseError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="; ".join(exc.errors)
        ) from exc

    try:
        skill = register_skill(
            db,
            manifest=manifest,
            submitted_by=user,
            raw_markdown=payload.manifest_markdown,
        )
    except AgentSkillValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="; ".join(exc.errors)
        ) from exc

    record_audit(
        db,
        request,
        "AGENT_SKILL_REGISTERED",
        user_id=user.id,
        details={"agent_skill_id": skill.id, "domain": skill.domain, "source": "modelo_md_import"},
    )
    db.commit()
    return skill


@router.patch("/{skill_id}/enable", response_model=AgentSkillRead)
def enable(
    skill_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
    _: AuthSession = Depends(require_authenticated_csrf),
) -> object:
    try:
        skill = enable_skill(db, skill_id)
    except AgentSkillNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    record_audit(db, request, "AGENT_SKILL_ENABLED", user_id=user.id, details={"agent_skill_id": skill_id})
    db.commit()
    return skill


@router.patch("/{skill_id}/disable", response_model=AgentSkillRead)
def disable(
    skill_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
    _: AuthSession = Depends(require_authenticated_csrf),
) -> object:
    try:
        skill = disable_skill(db, skill_id)
    except AgentSkillNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    record_audit(db, request, "AGENT_SKILL_DISABLED", user_id=user.id, details={"agent_skill_id": skill_id})
    db.commit()
    return skill


@router.get("/{skill_id}", response_model=AgentSkillRead)
def get_skill_detail(
    skill_id: str,
    db: Session = Depends(get_db),
    _: AuthSession = Depends(get_current_session),
) -> object:
    try:
        return get_skill(db, skill_id)
    except AgentSkillNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/requests/{request_id}/execute", response_model=OrchestrationExecutionRead)
async def execute_skills_for_request(
    request_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_technician),
    _: AuthSession = Depends(require_authenticated_csrf),
) -> OrchestrationExecutionRead:
    technical_request = _find_qualified_request(db, request_id, user)

    try:
        execution = await execute_orchestration_step(db, technical_request=technical_request, user=user)
    except NoAgentSkillsAvailableError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    record_audit(
        db,
        request,
        "AGENT_SKILL_ORCHESTRATION_EXECUTED",
        user_id=user.id,
        details={
            "technical_request_id": technical_request.id,
            "trace_id": technical_request.trace_id,
            "skills_invoked": len(execution.invocations),
            "quality_gate_approved": execution.verdict.approved,
        },
    )
    db.commit()

    return OrchestrationExecutionRead(
        results=execution.results,
        verdict=execution.verdict,
        invocations_count=len(execution.invocations),
        consolidated_response=ConsolidatedResponseRead.model_validate(execution.consolidated_response),
    )
