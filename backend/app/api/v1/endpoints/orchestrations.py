from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.dependencies import get_current_session
from app.core.database import get_db
from app.models import (
    AgentSkill,
    AgentSkillInvocation,
    AuthSession,
    FollowUpExchange,
    OrchestrationEvent,
    TechnicalRequest,
)
from app.schemas.orchestration import (
    AgentSkillInvocationResultRead,
    FollowUpExchangeRead,
    OrchestrationDetail,
    OrchestrationEventRead,
)

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
    return [
        AgentSkillInvocationResultRead(
            id=invocation.id,
            agent_skill_name=skill_name,
            status=invocation.status,
            confidence_level=invocation.confidence_level,
            result=invocation.result_payload,
            created_at=invocation.created_at,
        )
        for invocation, skill_name in rows
    ]


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
