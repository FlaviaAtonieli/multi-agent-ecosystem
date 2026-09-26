from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class OrchestrationEvent(Base):
    __tablename__ = "orchestration_events"
    __table_args__ = (
        UniqueConstraint(
            "technical_request_id",
            "sequence_number",
            name="uq_orchestration_event_request_sequence",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    technical_request_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("technical_requests.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    orchestration_run_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("orchestration_runs.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )
    sequence_number: Mapped[int] = mapped_column(nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    actor: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    technical_request = relationship("TechnicalRequest", back_populates="events")
    orchestration_run = relationship("OrchestrationRun", back_populates="events")
