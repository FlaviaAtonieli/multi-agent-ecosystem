"""RFC Apêndice C "Camada de Contratos": pure data contracts shared between the
Orchestrator and every Agent Skill (input/output schemas), with no dependency
on service-layer code -- kept separate from tool_interface.py's SkillExecutor
implementations (which DO call into app.services.llm_service) specifically so
app.schemas.orchestration can import SkillToolResult without a circular import
(schemas.orchestration -> tool_interface -> llm_service -> orchestration_service
-> schemas.orchestration).
"""

from typing import Literal

from pydantic import BaseModel, Field

from app.models import AgentSkill

ConfidenceLevel = Literal["ALTO", "MEDIO", "BAIXO"]


class SkillToolCall(BaseModel):
    """Mirrors solicitacao_analise_schema.json (Apêndice C da RFC), simplified
    to the fields the PoC executor actually consumes.

    Carries IDs, not prose: once a skill runs behind a real MCP transport
    (app/agent_catalog/mcp_servers/), it has its own database session and
    re-fetches the real rows instead of trusting a paraphrase from the caller.
    """

    trace_id: str
    technical_request_id: str
    user_id: str
    agent_skill_id: str
    analises_requeridas: list[str] = Field(default_factory=list)
    requested_model: str | None = None


class AgenteEmissor(BaseModel):
    nome: str
    versao_prompt: str | None = None
    dominio: Literal[
        "codigo_legado", "regras_negocio", "arquitetura_software", "seguranca_informacao"
    ]


class AchadoTecnico(BaseModel):
    item_identificado: str
    descricao_detalhada: str
    trecho_referenciado: str | None = None


class AnaliseEstruturada(BaseModel):
    resumo_executivo: str
    descobertas_tecnicas: list[AchadoTecnico] = Field(default_factory=list)
    impactos_mapeados: list[str] = Field(default_factory=list)


class Governanca(BaseModel):
    nivel_confianca: ConfidenceLevel
    justificativa_confianca: str
    referencias_catalogo: list[str] = Field(default_factory=list)


class SkillToolResult(BaseModel):
    """Mirrors resposta_especialista_schema.json (Apêndice C da RFC): the
    mandatory output contract for any Agent Skill in this ecosystem."""

    trace_id: str
    agente_emissor: AgenteEmissor
    analise_estruturada: AnaliseEstruturada
    governanca: Governanca


class SkillToolDescriptor(BaseModel):
    """Catalog-facing listing, backed directly by the `agent_skills` table —
    cheap and doesn't require talking to any skill's live MCP server. This is
    what `GET /agent-skills/tools` returns for browsing.

    It is distinct from the *live* `tools/list` discovery a real MCP `Client`
    performs against a skill's server right before invoking it (see
    `app/agent_catalog/mcp_client.py`), which reflects what that specific
    server actually exposes at that moment, not what the catalog has on file.
    """

    name: str
    description: str
    input_schema: dict
    output_schema: dict


def list_tools(skills: list[AgentSkill]) -> list[SkillToolDescriptor]:
    input_schema = SkillToolCall.model_json_schema()
    output_schema = SkillToolResult.model_json_schema()
    return [
        SkillToolDescriptor(
            name=f"agent_skill.{skill.id}",
            description=f"{skill.name} (domínio: {skill.domain}) — {skill.objective}",
            input_schema=input_schema,
            output_schema=output_schema,
        )
        for skill in skills
    ]
