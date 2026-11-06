from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, DateTime, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class EmbeddingCacheEntry(Base):
    """Vetor já gerado para um texto e modelo (ver app/rag/cache.py)."""

    __tablename__ = "embedding_cache"
    __table_args__ = (UniqueConstraint("model", "text_hash", name="uq_embedding_cache_model_text"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    text_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    embedding: Mapped[list[float]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
