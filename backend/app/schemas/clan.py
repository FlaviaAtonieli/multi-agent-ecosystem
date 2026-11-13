from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

ClanPolicyLiteral = Literal["ALL_MEMBERS", "OWNER_ONLY"]


class ClanCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    is_open: bool = Field(default=False, description="Se true, qualquer usuário pode entrar sozinho.")
    skills_policy: ClanPolicyLiteral = Field(
        default="ALL_MEMBERS", description="Quem pode registrar Agent Skills com visibilidade CLAN."
    )
    members_policy: ClanPolicyLiteral = Field(
        default="ALL_MEMBERS", description="Quem pode adicionar e remover membros."
    )


class ClanSettingsUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=2, max_length=120)
    is_open: bool | None = None
    skills_policy: ClanPolicyLiteral | None = None
    members_policy: ClanPolicyLiteral | None = None


class ClanMemberAdd(BaseModel):
    email: EmailStr


class ClanSkillAdd(BaseModel):
    agent_skill_id: str = Field(min_length=1, max_length=36)


class ClanMemberRead(BaseModel):
    user_id: str
    name: str
    email: str
    joined_at: datetime


class ClanRead(BaseModel):
    id: str
    name: str
    created_by_id: str
    created_at: datetime
    member_count: int
    is_open: bool
    skills_policy: ClanPolicyLiteral
    members_policy: ClanPolicyLiteral


class ClanDetailRead(BaseModel):
    id: str
    name: str
    created_by_id: str
    created_at: datetime
    members: list[ClanMemberRead]
    is_open: bool
    skills_policy: ClanPolicyLiteral
    members_policy: ClanPolicyLiteral


class ClanRepositoryAdd(BaseModel):
    url: str = Field(max_length=300, description="Endereço de um repositório público do GitHub.")

    @field_validator("url")
    @classmethod
    def github_only(cls, value: str) -> str:
        from app.services.repository_service import parse_github_url

        owner, name = parse_github_url(value)
        return f"https://github.com/{owner}/{name}"


class ClanRepositoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    url: str
    owner: str
    name: str
    status: Literal["PENDING", "INDEXING", "READY", "FAILED"]
    error_message: str | None
    file_count: int
    chunk_count: int
    created_at: datetime
    indexed_at: datetime | None
