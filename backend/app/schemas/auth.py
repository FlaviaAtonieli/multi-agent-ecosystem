from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.user import UserRead


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class AuthResponse(BaseModel):
    user: UserRead
    session_expires_at: datetime


class CsrfResponse(BaseModel):
    message: str = "Token CSRF preparado."


class SessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    ip_address: str | None
    user_agent: str | None
    expires_at: datetime
    last_seen_at: datetime
    created_at: datetime
    current: bool = False
