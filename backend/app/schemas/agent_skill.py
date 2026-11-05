from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.agent_catalog.contracts import SkillToolResult
from app.agent_manifest.manifest import DomainName
from app.quality_gate.service import QualityGateVerdict
from app.schemas.orchestration import ConsolidatedResponseRead

SkillVisibilityLiteral = Literal["OFFICIAL", "PRIVATE", "CLAN"]


class AgentSkillManifestImport(BaseModel):
    """RF02: import an existing Agent Skill from a raw modelo.md file."""

    manifest_markdown: str = Field(min_length=1)
    visibility: SkillVisibilityLiteral = "OFFICIAL"
    clan_id: str | None = Field(default=None, description="Obrigatório quando visibility='CLAN'.")


class AgentSkillManifestCreate(BaseModel):
    """RF01: assisted creation via a structured form, bypassing the modelo.md parser."""

    visibility: SkillVisibilityLiteral = "OFFICIAL"
    clan_id: str | None = Field(default=None, description="Obrigatório quando visibility='CLAN'.")
    name: str = Field(max_length=160)
    version: str = Field(max_length=30)
    author_origin: str
    domain: DomainName
    objective: str
    capabilities: list[str] = Field(default_factory=list)
    expected_inputs: list[str] = Field(default_factory=list)
    produced_outputs: list[str] = Field(default_factory=list)
    operating_limits: list[str] = Field(default_factory=list)
    input_contract_ref: str
    output_contract_ref: str
    security_rules: list[str] = Field(default_factory=list)
    usage_examples: list[str] = Field(default_factory=list)
    validation_criteria: list[str] = Field(default_factory=list)
    uses_external_services: bool = False
    persona_instructions: str | None = Field(default=None, max_length=4000)


class AgentSkillRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    version: str
    domain: str
    status: str
    enabled: bool
    author_origin: str
    objective: str
    input_contract_ref: str
    output_contract_ref: str
    uses_external_services: bool
    owner_id: str | None
    visibility: str
    clan_id: str | None
    persona_instructions: str | None
    manifest_json: dict
    validated_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AgentSkillRankingRead(BaseModel):
    id: str
    name: str
    domain: str
    version: str
    usage_count: int


class AgentSkillToolDescriptorRead(BaseModel):
    name: str
    description: str
    input_schema: dict
    output_schema: dict


class OrchestrationExecutionRead(BaseModel):
    results: list[SkillToolResult]
    verdict: QualityGateVerdict
    invocations_count: int
    consolidated_response: ConsolidatedResponseRead


class OrchestrationStartRead(BaseModel):
    trace_id: str
    status: str


class AgentSkillExecutionRequest(BaseModel):
    """Optional model override for this specific execution (RFC 5.2 Model Gateway:
    picking among LLM_ALLOWED_MODELS, not an arbitrary string). None keeps the
    configured LLM_MODEL default."""

    model: str | None = Field(default=None, max_length=200)


class SkillSuggestionRequest(BaseModel):
    clan_id: str = Field(min_length=1, max_length=36)
    title: str | None = Field(default=None, max_length=160)
    problem: str = Field(min_length=1, max_length=10_000)
    objective: str = Field(min_length=1, max_length=5_000)
    context: str | None = Field(default=None, max_length=20_000)


class SkillSuggestionItem(BaseModel):
    id: str
    name: str
    domain: str
    objective: str
    score: float = Field(description="Similaridade de cosseno com a solicitação. Não é uma probabilidade.")


class SkillSuggestionsRead(BaseModel):
    available: bool = Field(description="False quando o provedor de embeddings não está disponível.")
    suggestions: list[SkillSuggestionItem]
    best_clan_score: float | None
    covered_by_clan: bool
    catalog_gap: bool = Field(description="True quando nada no catálogo chega ao limite de similaridade.")
    can_add_to_clan: bool
