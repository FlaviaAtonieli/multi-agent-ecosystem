from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class FollowUpExchange(Base):
    """A single question-and-answer round after the initial orchestration
    execution, kept as its own row so the conversation history survives --
    unlike ConsolidatedResponse (one per TechnicalRequest, RFC §5.3's single
    "resposta final"), a request can have many follow-up exchanges.
    """

    __tablename__ = "follow_up_exchanges"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    technical_request_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("technical_requests.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    trace_id: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    asked_by_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    target_domain: Mapped[str | None] = mapped_column(String(60), nullable=True)
    synthesis: Mapped[str] = mapped_column(Text, nullable=False)
    results: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    overall_confidence_level: Mapped[str] = mapped_column(String(10), nullable=False)
    quality_gate_approved: Mapped[bool] = mapped_column(Boolean, nullable=False)
    requires_human_review: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    technical_request = relationship("TechnicalRequest", back_populates="follow_up_exchanges")
    asked_by = relationship("User")
