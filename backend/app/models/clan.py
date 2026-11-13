from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint, false, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Clan(Base):
    """Grupo que qualquer pessoa cria, sem aprovação: quem cria vira membro e dono.

    Quem adiciona membros ou cadastra skills do comitê é configurável (members_policy,
    skills_policy), e um comitê aberto aceita qualquer pessoa.
    """

    __tablename__ = "clans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    created_by_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    # Regras configuradas na criação (migration 0015). O "dono" é created_by_id.
    # is_open: qualquer usuário pode entrar sozinho (POST /clans/{id}/join).
    # skills_policy / members_policy: "ALL_MEMBERS" ou "OWNER_ONLY" -- quem pode
    # registrar Agent Skills CLAN / adicionar e remover membros. O dono sempre pode.
    is_open: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false(), nullable=False)
    skills_policy: Mapped[str] = mapped_column(
        String(20), default="ALL_MEMBERS", server_default="ALL_MEMBERS", nullable=False
    )
    members_policy: Mapped[str] = mapped_column(
        String(20), default="ALL_MEMBERS", server_default="ALL_MEMBERS", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    created_by = relationship("User", foreign_keys=[created_by_id])
    memberships = relationship("ClanMembership", back_populates="clan", cascade="all, delete-orphan")


class ClanSkill(Base):
    """Uma Agent Skill disponível num comitê. Só as skills do comitê escolhido rodam numa
    orquestração, o que evita chamar skills fora do assunto. Uma skill pode estar em
    vários comitês, inclusive os de outras pessoas, quando é publicada."""

    __tablename__ = "clan_skills"
    __table_args__ = (UniqueConstraint("clan_id", "agent_skill_id", name="uq_clan_skill"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    clan_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("clans.id", ondelete="CASCADE"), index=True, nullable=False
    )
    agent_skill_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("agent_skills.id", ondelete="CASCADE"), index=True, nullable=False
    )
    added_by_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ClanMembership(Base):
    """Ligação entre usuário e comitê; uma pessoa pode estar em vários. added_by_id registra
    quem adicionou quem, já que não há convite nem aprovação.
    """

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
