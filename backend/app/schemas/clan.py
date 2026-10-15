from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

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
