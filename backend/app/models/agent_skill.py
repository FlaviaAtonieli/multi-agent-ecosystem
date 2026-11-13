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
    # 200 caracteres não bastavam: os contratos do modelo.md trazem uma descrição depois
    # do nome do schema. Só apareceu no PostgreSQL, porque o SQLite dos testes não confere
    # o tamanho do VARCHAR.
    input_contract_ref: Mapped[str] = mapped_column(String(500), nullable=False)
    output_contract_ref: Mapped[str] = mapped_column(String(500), nullable=False)
    uses_external_services: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    submitted_by_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    # None = skill oficial do catálogo. Preenchido = skill criada por essa pessoa.
    owner_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=True
    )
    visibility: Mapped[str] = mapped_column(
        String(20), index=True, nullable=False, default="OFFICIAL"
    )
    # Só com visibility == "CLAN": o clã da skill. SET NULL, e não CASCADE: se o clã
    # for apagado, a skill fica visível só para o dono, mas não some junto.
    clan_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("clans.id", ondelete="SET NULL"), index=True, nullable=True
    )
    # Instruções da skill no prompt do planejador (app/llm/prompts.py). As 4 oficiais
    # originais não têm: seguem só pela área.
    persona_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Motor de sugestão. Adiado porque só ele lê o vetor, e o catálogo lista todas as skills.
    embedding: Mapped[list[float] | None] = mapped_column(JSON, nullable=True, deferred=True)
    embedding_text_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
