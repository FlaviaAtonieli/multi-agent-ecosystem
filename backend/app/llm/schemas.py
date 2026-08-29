from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LLMPlanRequest(BaseModel):
    technical_request_id: str
    trace_id: str
    title: str = Field(max_length=160)
    problem: str
    objective: str
    context: str | None = None
    restrictions: list[str] = Field(default_factory=list)
    retrieved_context: str | None = None
    # RFC §6.1 "Proteção de Contexto": which Agent Skill domain this specific
    # call is scoped to, when invoked on behalf of one skill (None for the raw
    # /llm/plan endpoint, which has no single skill to scope to).
    analysis_domain_label: str | None = None


class LLMPlan(BaseModel):
    summary: str = Field(min_length=1, max_length=3000)
    required_agents: list[str] = Field(default_factory=list, max_length=20)
    required_skills: list[str] = Field(default_factory=list, max_length=30)
    risks: list[str] = Field(default_factory=list, max_length=30)
    missing_information: list[str] = Field(default_factory=list, max_length=30)
    requires_human_approval: bool = True


class LLMUsage(BaseModel):
    input_tokens: int | None = None
    output_tokens: int | None = None


class LLMProviderResult(BaseModel):
    plan: LLMPlan
    provider_response_id: str | None = None
    provider_request_id: str | None = None
    usage: LLMUsage = Field(default_factory=LLMUsage)


class LLMStatusRead(BaseModel):
    enabled: bool
    provider: str
    model: str
    configured: bool
    allowed_models: list[str]
    max_input_chars: int
    max_output_tokens: int
    requests_per_hour_technician: int
    store_provider_response: bool
    store_result_content: bool
    daily_token_limit_per_user: int
    tokens_used_today: int


class LLMPlanResponse(BaseModel):
    technical_request_id: str
    trace_id: str
    llm_call_id: str
    provider: str
    model: str
    plan: LLMPlan
    usage: LLMUsage
    completed_at: datetime


class LLMInvocationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    trace_id: str
    llm_call_id: str
    provider: str
    model: str
    purpose: str
    prompt_template_id: str
    prompt_template_version: str
    input_hash: str
    output_hash: str | None
    provider_response_id: str | None
    provider_request_id: str | None
    input_tokens: int | None
    output_tokens: int | None
    latency_ms: int | None
    status: str
    error_code: str | None
    redacted_fields_count: int
    input_truncated: bool
    retrieved_chunk_ids: list[str] | None
    created_at: datetime
    completed_at: datetime | None
