from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


def strict_json_schema(model: type[BaseModel]) -> dict:
    """Schema JSON aceito pelo modo strict de Structured Outputs da OpenAI.

    O Pydantic só põe em "required" os campos sem valor padrão, mas o modo strict exige
    todos. Sem isso, o openai/gpt-5-mini recusava toda chamada com 400
    "invalid_json_schema"; o modelo gratuito aceitava o mesmo schema, por isso o erro
    só apareceu com um modelo strict.
    """
    schema = model.model_json_schema()
    for object_schema in [schema, *schema.get("$defs", {}).values()]:
        object_schema["required"] = list(object_schema["properties"].keys())
        object_schema["additionalProperties"] = False
    return schema


class LLMPlanRequest(BaseModel):
    technical_request_id: str
    trace_id: str
    title: str = Field(max_length=160)
    problem: str
    objective: str
    context: str | None = None
    restrictions: list[str] = Field(default_factory=list)
    retrieved_context: str | None = None
    # Área da skill a que esta chamada se limita (proteção de contexto); None no
    # endpoint /llm/plan, que não é de uma skill.
    analysis_domain_label: str | None = None
    # Só numa pergunta de acompanhamento: vai ao fim do prompt, depois do problema, do
    # objetivo e do contexto originais.
    additional_question: str | None = None
    # Instruções da skill (persona), quando ela tem.
    persona_instructions: str | None = None
    # Texto dos anexos, identificado pelo nome do arquivo, sanitizado e truncado como
    # os outros campos.
    attachments_context: str | None = None
    # Entregas das skills que rodaram antes, para a skill que escreve código
    # (app/services/team_context.py). Sanitizadas e truncadas como o resto.
    team_context: str | None = None


class LLMGeneratedFile(BaseModel):
    filename: str
    content: str


class LLMPlan(BaseModel):
    summary: str = Field(min_length=1, max_length=3000)
    required_agents: list[str] = Field(default_factory=list, max_length=20)
    required_skills: list[str] = Field(default_factory=list, max_length=30)
    risks: list[str] = Field(default_factory=list, max_length=30)
    missing_information: list[str] = Field(default_factory=list, max_length=30)
    requires_human_approval: bool = True
    # Sem limite aqui: exceder não deve invalidar a análise inteira. O limite fica em
    # app/services/artifact_service.py, que recusa só os arquivos em excesso.
    generated_files: list[LLMGeneratedFile] = Field(default_factory=list)


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
    temperature: float | None = None
    seed: int | None = None
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
