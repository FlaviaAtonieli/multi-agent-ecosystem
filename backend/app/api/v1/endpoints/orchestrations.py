from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.dependencies import get_current_session, require_authenticated_csrf
from app.core.database import get_db
from app.models import (
    AgentSkill,
    AgentSkillInvocation,
    AuthSession,
    FollowUpExchange,
    OrchestrationEvent,
    SkillArtifact,
    TechnicalRequest,
)
from app.schemas.orchestration import (
    AgentResponseFeedbackRead,
    AgentResponseFeedbackWrite,
    AgentSkillInvocationResultRead,
    FollowUpExchangeRead,
    OrchestrationDetail,
    OrchestrationEventRead,
    SkillArtifactContentRead,
    SkillArtifactRead,
)
from app.services.artifact_service import build_zip
from app.services.feedback_service import feedback_by_invocation, remove_feedback, save_feedback

router = APIRouter(prefix="/orchestrations", tags=["Orquestrações"])


def find_by_trace_id(db: Session, trace_id: str, owner_id: str) -> TechnicalRequest:
    technical_request = db.scalar(
        select(TechnicalRequest)
        .options(
            selectinload(TechnicalRequest.orchestration_run),
            selectinload(TechnicalRequest.events),
        )
        .where(
            TechnicalRequest.trace_id == trace_id,
            TechnicalRequest.owner_id == owner_id,
        )
    )
    if technical_request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Orquestração não encontrada.",
        )
    return technical_request


@router.get("/{trace_id}", response_model=OrchestrationDetail)
def get_orchestration(
    trace_id: str,
    db: Session = Depends(get_db),
    current_session: AuthSession = Depends(get_current_session),
) -> OrchestrationDetail:
    technical_request = find_by_trace_id(db, trace_id, current_session.user_id)
    if technical_request.orchestration_run is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A solicitação não possui uma execução de orquestração associada.",
        )
    return OrchestrationDetail(
        technical_request=technical_request,
        run=technical_request.orchestration_run,
        events=list(technical_request.events),
    )


@router.get("/{trace_id}/events", response_model=list[OrchestrationEventRead])
def get_orchestration_events(
    trace_id: str,
    db: Session = Depends(get_db),
    current_session: AuthSession = Depends(get_current_session),
) -> list[OrchestrationEvent]:
    technical_request = find_by_trace_id(db, trace_id, current_session.user_id)
    return list(technical_request.events)


@router.get("/{trace_id}/skill-results", response_model=list[AgentSkillInvocationResultRead])
def get_orchestration_skill_results(
    trace_id: str,
    db: Session = Depends(get_db),
    current_session: AuthSession = Depends(get_current_session),
) -> list[AgentSkillInvocationResultRead]:
    technical_request = find_by_trace_id(db, trace_id, current_session.user_id)
    rows = db.execute(
        select(AgentSkillInvocation, AgentSkill.name)
        .join(AgentSkill, AgentSkillInvocation.agent_skill_id == AgentSkill.id)
        .where(
            AgentSkillInvocation.technical_request_id == technical_request.id,
            AgentSkillInvocation.status == "COMPLETED",
        )
        .order_by(AgentSkillInvocation.created_at.asc())
    ).all()
    feedback = feedback_by_invocation(db, [invocation.id for invocation, _ in rows])
    return [
        AgentSkillInvocationResultRead(
            id=invocation.id,
            agent_skill_name=skill_name,
            status=invocation.status,
            confidence_level=invocation.confidence_level,
            result=invocation.result_payload,
            created_at=invocation.created_at,
            feedback=feedback.get(invocation.id),
        )
        for invocation, skill_name in rows
    ]


@router.put("/{trace_id}/skill-results/{invocation_id}/feedback", response_model=AgentResponseFeedbackRead)
def rate_skill_result(
    trace_id: str,
    invocation_id: str,
    payload: AgentResponseFeedbackWrite,
    request: Request,
    db: Session = Depends(get_db),
    current_session: AuthSession = Depends(require_authenticated_csrf),
) -> AgentResponseFeedbackRead:
    technical_request = find_by_trace_id(db, trace_id, current_session.user_id)
    feedback = save_feedback(
        db,
        request,
        technical_request=technical_request,
        invocation_id=invocation_id,
        user_id=current_session.user_id,
        data=payload,
    )
    return AgentResponseFeedbackRead.model_validate(feedback)


@router.delete("/{trace_id}/skill-results/{invocation_id}/feedback", status_code=status.HTTP_204_NO_CONTENT)
def remove_skill_result_rating(
    trace_id: str,
    invocation_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_session: AuthSession = Depends(require_authenticated_csrf),
) -> Response:
    technical_request = find_by_trace_id(db, trace_id, current_session.user_id)
    remove_feedback(
        db,
        request,
        technical_request=technical_request,
        invocation_id=invocation_id,
        user_id=current_session.user_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{trace_id}/follow-ups", response_model=list[FollowUpExchangeRead])
def get_orchestration_follow_ups(
    trace_id: str,
    db: Session = Depends(get_db),
    current_session: AuthSession = Depends(get_current_session),
) -> list[FollowUpExchange]:
    technical_request = find_by_trace_id(db, trace_id, current_session.user_id)
    return list(
        db.scalars(
            select(FollowUpExchange)
            .where(FollowUpExchange.technical_request_id == technical_request.id)
            .order_by(FollowUpExchange.sequence_number.asc())
        )
    )


def _artifact_rows(db: Session, technical_request_id: str):
    return db.execute(
        select(SkillArtifact, AgentSkill)
        .join(AgentSkillInvocation, SkillArtifact.invocation_id == AgentSkillInvocation.id)
        .join(AgentSkill, AgentSkillInvocation.agent_skill_id == AgentSkill.id)
        .where(SkillArtifact.technical_request_id == technical_request_id)
        .order_by(SkillArtifact.created_at.asc(), SkillArtifact.filename.asc())
    ).all()


def _artifact_fields(artifact: SkillArtifact, skill: AgentSkill) -> dict:
    return {
        "id": artifact.id,
        "filename": artifact.filename,
        "size_bytes": artifact.size_bytes,
        "agent_skill_name": skill.name,
        "domain": skill.domain,
        "created_at": artifact.created_at,
    }


def _find_artifact(
    db: Session, technical_request_id: str, artifact_id: str
) -> tuple[SkillArtifact, AgentSkill]:
    for artifact, skill in _artifact_rows(db, technical_request_id):
        if artifact.id == artifact_id:
            return artifact, skill
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Arquivo não encontrado.")


def _attachment_header(filename: str) -> str:
    ascii_name = filename.encode("ascii", "ignore").decode().replace('"', "").replace("\\", "") or "arquivo"
    return f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(filename)}"


@router.get("/{trace_id}/artifacts", response_model=list[SkillArtifactRead])
def list_artifacts(
    trace_id: str,
    db: Session = Depends(get_db),
    current_session: AuthSession = Depends(get_current_session),
) -> list[SkillArtifactRead]:
    technical_request = find_by_trace_id(db, trace_id, current_session.user_id)
    return [
        SkillArtifactRead(**_artifact_fields(artifact, skill))
        for artifact, skill in _artifact_rows(db, technical_request.id)
    ]


@router.get("/{trace_id}/artifacts.zip", response_class=Response)
def download_all_artifacts(
    trace_id: str,
    db: Session = Depends(get_db),
    current_session: AuthSession = Depends(get_current_session),
) -> Response:
    technical_request = find_by_trace_id(db, trace_id, current_session.user_id)
    rows = _artifact_rows(db, technical_request.id)
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Esta orquestração não tem arquivos."
        )
    content = build_zip((skill.domain, artifact.filename, artifact.content) for artifact, skill in rows)
    return Response(
        content=content,
        media_type="application/zip",
        headers={"Content-Disposition": _attachment_header(f"{technical_request.trace_id}.zip")},
    )


@router.get("/{trace_id}/artifacts/{artifact_id}", response_model=SkillArtifactContentRead)
def get_artifact(
    trace_id: str,
    artifact_id: str,
    db: Session = Depends(get_db),
    current_session: AuthSession = Depends(get_current_session),
) -> SkillArtifactContentRead:
    technical_request = find_by_trace_id(db, trace_id, current_session.user_id)
    artifact, skill = _find_artifact(db, technical_request.id, artifact_id)
    return SkillArtifactContentRead(**_artifact_fields(artifact, skill), content=artifact.content)


@router.get("/{trace_id}/artifacts/{artifact_id}/download", response_class=Response)
def download_artifact(
    trace_id: str,
    artifact_id: str,
    db: Session = Depends(get_db),
    current_session: AuthSession = Depends(get_current_session),
) -> Response:
    technical_request = find_by_trace_id(db, trace_id, current_session.user_id)
    artifact, _ = _find_artifact(db, technical_request.id, artifact_id)
    # octet-stream com attachment: um HTML gerado pelo modelo nunca roda no site.
    return Response(
        content=artifact.content.encode("utf-8", errors="replace"),
        media_type="application/octet-stream",
        headers={"Content-Disposition": _attachment_header(artifact.filename.rsplit("/", 1)[-1])},
    )
