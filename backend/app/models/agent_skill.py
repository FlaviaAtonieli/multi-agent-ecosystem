from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AgentSkill(Base):
    __tablename__ = "agent_skills"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    version: Mapped[str] = mapped_column(String(30), nullable=False)
    domain: Mapped[str] = mapped_column(String(60), index=True, nullable=False)
    status: Mapped[str] = mapped_column(
        String(30), index=True, nullable=False, default="pending_validation"
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    author_origin: Mapped[str] = mapped_column(String(160), nullable=False)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    manifest_markdown: Mapped[str | None] = mapped_column(Text, nullable=True)
    manifest_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    # 200 chars proved too tight for real content: modelo.md's "Contrato de
    # Entrada/Saida" sections carry a descriptive gloss after the schema name
    # (RFC Apendice C wording), not just a short slug -- e.g. every shipped
    # fixture's output_contract_ref is 205 chars. Only caught testing against
    # real PostgreSQL; the test suite's SQLite never enforces VARCHAR length.
    input_contract_ref: Mapped[str] = mapped_column(String(500), nullable=False)
    output_contract_ref: Mapped[str] = mapped_column(String(500), nullable=False)
    uses_external_services: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    submitted_by_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
