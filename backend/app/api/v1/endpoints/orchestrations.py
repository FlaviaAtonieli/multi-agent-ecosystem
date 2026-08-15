from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.dependencies import get_current_session
from app.core.database import get_db
from app.models import AuthSession, OrchestrationEvent, TechnicalRequest
from app.schemas.orchestration import OrchestrationDetail, OrchestrationEventRead


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
