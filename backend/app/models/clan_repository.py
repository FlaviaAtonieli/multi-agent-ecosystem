from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ClanRepository(Base):
    """Repositório público do GitHub que alimenta a base de conhecimento de um comitê.

    O código é baixado e lido como texto, nunca executado. Os trechos ficam ligados ao
    comitê, e só as orquestrações dele os encontram.
    """

    __tablename__ = "clan_repositories"
    __table_args__ = (UniqueConstraint("clan_id", "owner", "name", name="uq_clan_repository"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    clan_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("clans.id", ondelete="CASCADE"), index=True, nullable=False
    )
    owner: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    url: Mapped[str] = mapped_column(String(300), nullable=False)
    # PENDING -> INDEXING -> READY | FAILED
    status: Mapped[str] = mapped_column(String(20), index=True, nullable=False, default="PENDING")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    added_by_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
