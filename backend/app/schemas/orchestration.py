from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TechnicalRequestCreate(BaseModel):
    title: str = Field(min_length=5, max_length=160)
    problem: str = Field(min_length=10, max_length=10_000)
    objective: str = Field(min_length=5, max_length=5_000)
    context: str | None = Field(default=None, max_length=20_000)
    restrictions: list[str] = Field(default_factory=list, max_length=20)
    requested_domains: list[str] = Field(default_factory=list, max_length=10)

    @field_validator("title", "problem", "objective")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("context")
    @classmethod
    def normalize_optional_context(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("restrictions")
    @classmethod
    def normalize_restrictions(cls, values: list[str]) -> list[str]:
        normalized = [item.strip() for item in values if item.strip()]
        return normalized[:20]

    @field_validator("requested_domains")
    @classmethod
    def dedupe_requested_domains(cls, values: list[str]) -> list[str]:
        seen: list[str] = []
        for value in values:
            if value not in seen:
                seen.append(value)
        return seen


class TechnicalRequestContextUpdate(BaseModel):
    context: str = Field(min_length=10, max_length=20_000)

    @field_validator("context")
    @classmethod
    def strip_context(cls, value: str) -> str:
        return value.strip()


class TechnicalRequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    trace_id: str
    title: str
    problem: str
    objective: str
    context: str | None
    restrictions: list[str]
    requested_domains: list[str]
    status: str
    created_at: datetime
    updated_at: datetime


class OrchestrationRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: str
    current_stage: str
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class OrchestrationEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    sequence_number: int
    event_type: str
    actor: str
    title: str
    message: str
    payload: dict
    created_at: datetime


class OrchestrationDetail(BaseModel):
    technical_request: TechnicalRequestRead
    run: OrchestrationRunRead
    events: list[OrchestrationEventRead]
