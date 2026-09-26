from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AgentSkillInvocation(Base):
    __tablename__ = "agent_skill_invocations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    technical_request_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("technical_requests.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    orchestration_run_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("orchestration_runs.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    agent_skill_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("agent_skills.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    trace_id: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    invocation_id: Mapped[str] = mapped_column(String(36), unique=True, index=True, nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    output_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(30), index=True, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    confidence_level: Mapped[str | None] = mapped_column(String(10), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    result_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
