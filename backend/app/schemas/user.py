import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


def _validate_password_strength(value: str) -> str:
    checks = [
        (r"[a-z]", "uma letra minúscula"),
        (r"[A-Z]", "uma letra maiúscula"),
        (r"\d", "um número"),
        (r"[^A-Za-z0-9]", "um caractere especial"),
    ]
    missing = [label for pattern, label in checks if not re.search(pattern, value)]
    if missing:
        raise ValueError("A senha deve conter " + ", ".join(missing) + ".")
    return value


class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return " ".join(value.strip().split())

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        return _validate_password_strength(value)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    email: EmailStr
    role: str
    is_active: bool
    avatar_url: str | None
    created_at: datetime
    onboarding_completed_at: datetime | None
    has_password: bool = False


class UserNameUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=80)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return " ".join(value.strip().split())


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=12, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_new_password_strength(cls, value: str) -> str:
        return _validate_password_strength(value)


class AdminUserRead(UserRead):
    tokens_used_today: int
    daily_token_limit_per_user: int


class UserStatusUpdate(BaseModel):
    is_active: bool


class UserRoleUpdate(BaseModel):
    role: Literal["USER", "TECHNICIAN", "REVIEWER", "ADMIN"]
