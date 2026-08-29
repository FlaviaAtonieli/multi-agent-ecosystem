from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.agent_catalog.contracts import SkillToolResult
from app.agent_manifest.manifest import DomainLiteral
from app.quality_gate.service import QualityGateVerdict
from app.schemas.orchestration import ConsolidatedResponseRead


class AgentSkillManifestImport(BaseModel):
    """RF02: import an existing Agent Skill from a raw modelo.md file."""

    manifest_markdown: str = Field(min_length=1)


class AgentSkillManifestCreate(BaseModel):
    """RF01: assisted creation via a structured form, bypassing the modelo.md parser."""

    name: str = Field(max_length=160)
    version: str = Field(max_length=30)
    author_origin: str
    domain: DomainLiteral
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
    validated_at: datetime | None
    created_at: datetime
    updated_at: datetime


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


class AgentSkillExecutionRequest(BaseModel):
    """Optional model override for this specific execution (RFC 5.2 Model Gateway:
    picking among LLM_ALLOWED_MODELS, not an arbitrary string). None keeps the
    configured LLM_MODEL default."""

    model: str | None = Field(default=None, max_length=200)
