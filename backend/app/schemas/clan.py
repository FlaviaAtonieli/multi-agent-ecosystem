from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class ClanCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)


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


class ClanDetailRead(BaseModel):
    id: str
    name: str
    created_by_id: str
    created_at: datetime
    members: list[ClanMemberRead]
