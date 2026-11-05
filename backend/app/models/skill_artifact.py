from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SkillArtifact(Base):
    """Arquivo entregue por uma Agent Skill (ver app/services/artifact_service.py)."""

    __tablename__ = "skill_artifacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    technical_request_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("technical_requests.id", ondelete="CASCADE"), index=True, nullable=False
    )
    invocation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("agent_skill_invocations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
