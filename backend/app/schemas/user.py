import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


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


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    email: EmailStr
    role: str
    is_active: bool
    created_at: datetime


class UserStatusUpdate(BaseModel):
    is_active: bool
