from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.agent_catalog.contracts import SkillToolResult
from app.agent_manifest.manifest import DomainLiteral


class TechnicalRequestCreate(BaseModel):
    title: str = Field(min_length=5, max_length=160)
    problem: str = Field(min_length=10, max_length=10_000)
    objective: str = Field(min_length=5, max_length=5_000)
    context: str | None = Field(default=None, max_length=20_000)
    restrictions: list[str] = Field(default_factory=list, max_length=20)
    requested_domains: list[DomainLiteral] = Field(default_factory=list, max_length=10)

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


class ConsolidatedResponseRead(BaseModel):
    """RFC §5.3 "Resposta Final Consolidada": the single synthesized answer,
    distinct from each Agent Skill's partial response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    trace_id: str
    technical_synthesis: str
    recommendations: list[str]
    risks: list[str]
    limitations: list[str]
    participating_agents: list[str]
    overall_confidence_level: str
    quality_gate_approved: bool
    requires_human_review: bool
    invocation_ids: list[str]
    created_at: datetime


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
    consolidated_response: ConsolidatedResponseRead | None = None


class TechnicalRequestReview(BaseModel):
    decision: Literal["approve", "reject"]
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("notes")
    @classmethod
    def normalize_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


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


class AgentSkillInvocationResultRead(BaseModel):
    """Persisted per-skill result (AgentSkillInvocation.result_payload), so the
    detailed breakdown survives a page reload -- not just the ephemeral response
    of POST /agent-skills/requests/{id}/execute."""

    id: str
    agent_skill_name: str
    status: str
    confidence_level: str | None
    result: SkillToolResult | None
    created_at: datetime


class FollowUpQuestionCreate(BaseModel):
    """A question asked after the initial execution, continuing the same
    orchestration chain (trace_id). target_domain=None broadcasts to every
    domain the original execution used; set it to aim the question at one
    specific Agent Skill domain instead."""

    question: str = Field(min_length=5, max_length=5_000)
    target_domain: DomainLiteral | None = Field(default=None)
    model: str | None = Field(default=None, max_length=200)

    @field_validator("question")
    @classmethod
    def strip_question(cls, value: str) -> str:
        return value.strip()


class FollowUpExchangeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    sequence_number: int
    question: str
    target_domain: str | None
    synthesis: str
    results: list[SkillToolResult]
    overall_confidence_level: str
    quality_gate_approved: bool
    requires_human_review: bool
    created_at: datetime
