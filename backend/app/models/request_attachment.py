from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class RequestAttachment(Base):
    """Documento anexado ao contexto de uma solicitação. Só texto: o conteúdo é lido como
    UTF-8 no envio (ver attachment_allowed_extensions em app/core/config.py).
    """

    __tablename__ = "request_attachments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    technical_request_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("technical_requests.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    uploaded_by_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    technical_request = relationship("TechnicalRequest", back_populates="attachments")
    uploaded_by = relationship("User")
