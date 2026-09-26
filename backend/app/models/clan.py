from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Clan(Base):
    """A self-service group any user can create (RFC visibility tier `CLAN` on
    AgentSkill, planned since migration 0010 but never built out). No approval
    flow: the creator becomes a member automatically, and any current member
    can add/remove others (see ClanMembership) -- confirmed as the intended
    scope with the project author, not a leftover placeholder."""

    __tablename__ = "clans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    created_by_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    created_by = relationship("User", foreign_keys=[created_by_id])
    memberships = relationship("ClanMembership", back_populates="clan", cascade="all, delete-orphan")


class ClanMembership(Base):
    """Many-to-many join between User and Clan -- a user can belong to several
    clans at once (confirmed scope). `added_by_id` keeps a lightweight audit
    trail of who added whom, since membership has no approval/invite step."""

    __tablename__ = "clan_memberships"
    __table_args__ = (UniqueConstraint("clan_id", "user_id", name="uq_clan_membership"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    clan_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("clans.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    added_by_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    clan = relationship("Clan", back_populates="memberships")
    user = relationship("User", foreign_keys=[user_id])
    added_by = relationship("User", foreign_keys=[added_by_id])
