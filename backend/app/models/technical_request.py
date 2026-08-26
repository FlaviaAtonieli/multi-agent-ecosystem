from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TechnicalRequest(Base):
    __tablename__ = "technical_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    owner_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    trace_id: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    problem: Mapped[str] = mapped_column(Text, nullable=False)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    context: Mapped[str | None] = mapped_column(Text, nullable=True)
    restrictions: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    requested_domains: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(32), index=True, nullable=False, default="RECEIVED")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    owner = relationship("User", back_populates="technical_requests")
    orchestration_run = relationship(
        "OrchestrationRun",
        back_populates="technical_request",
        uselist=False,
        cascade="all, delete-orphan",
    )
    events = relationship(
        "OrchestrationEvent",
        back_populates="technical_request",
        cascade="all, delete-orphan",
        order_by="OrchestrationEvent.sequence_number",
    )
    consolidated_response = relationship(
        "ConsolidatedResponse",
        back_populates="technical_request",
        uselist=False,
        cascade="all, delete-orphan",
    )
