from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ConsolidatedResponse(Base):
    """RFC §5.3 "Resposta Final Consolidada": the single synthesized answer
    delivered to the user, distinct from each Agent Skill's partial response
    (AgentSkillInvocation.result_payload). One per TechnicalRequest.
    """

    __tablename__ = "consolidated_responses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    technical_request_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("technical_requests.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    trace_id: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    technical_synthesis: Mapped[str] = mapped_column(Text, nullable=False)
    recommendations: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    risks: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    limitations: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    participating_agents: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    overall_confidence_level: Mapped[str] = mapped_column(String(10), nullable=False)
    quality_gate_approved: Mapped[bool] = mapped_column(Boolean, nullable=False)
    requires_human_review: Mapped[bool] = mapped_column(Boolean, nullable=False)
    invocation_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    technical_request = relationship("TechnicalRequest", back_populates="consolidated_response")
