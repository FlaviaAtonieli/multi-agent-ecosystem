"""Contratos trocados entre o orquestrador e as Agent Skills (entrada e saída).

Ficam fora do tool_interface.py, que chama o llm_service, para que
app.schemas.orchestration importe SkillToolResult sem import circular.
"""

from typing import Literal

from pydantic import BaseModel, Field

from app.models import AgentSkill

ConfidenceLevel = Literal["ALTO", "MEDIO", "BAIXO"]


class SkillToolCall(BaseModel):
    """Chamada de uma skill: leva ids, não texto.

    O servidor MCP da skill abre a própria sessão de banco e busca de novo as linhas
    reais, em vez de confiar num resumo de quem chamou.
    """

    trace_id: str
    technical_request_id: str
    user_id: str
    agent_skill_id: str
    analises_requeridas: list[str] = Field(default_factory=list)
    requested_model: str | None = None
    additional_question: str | None = None
    # Entregas das skills que rodaram antes, para as que escrevem código (ver
    # app/services/team_context.py).
    team_context: str | None = None


class AgenteEmissor(BaseModel):
    nome: str
    versao_prompt: str | None = None
    dominio: str = Field(max_length=60)


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


class ArquivoGerado(BaseModel):
    """Arquivo de texto entregue pela skill. Só viaja do servidor MCP até o Orquestrador,
    que valida o nome e guarda o conteúdo (ver app/services/artifact_service.py)."""

    nome: str
    conteudo: str


class SkillToolResult(BaseModel):
    """Contrato de saída obrigatório de toda Agent Skill (resposta_especialista_schema.json,
    Apêndice C da RFC).
    """

    trace_id: str
    agente_emissor: AgenteEmissor
    analise_estruturada: AnaliseEstruturada
    governanca: Governanca
    arquivos: list[ArquivoGerado] = Field(default_factory=list)


class SkillToolDescriptor(BaseModel):
    """Item do catálogo, lido da tabela agent_skills (GET /agent-skills/tools).

    Não conversa com o servidor MCP. A descoberta ao vivo (tools/list) acontece em
    mcp_client.py, logo antes de cada chamada, e mostra o que o servidor expõe de fato.
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
