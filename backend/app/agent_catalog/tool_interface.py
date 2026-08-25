from abc import ABC, abstractmethod
from typing import Literal

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AgentSkill, KnowledgeChunk, LLMInvocation, TechnicalRequest, User
from app.services.llm_service import generate_technical_plan

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


class AgenteEmissor(BaseModel):
    nome: str
    versao_prompt: str | None = None
    dominio: Literal["codigo_legado", "regras_negocio", "arquitetura_software"]


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


class SkillExecutor(ABC):
    @abstractmethod
    def execute(
        self,
        db: Session,
        *,
        skill: AgentSkill,
        technical_request: TechnicalRequest,
        user: User,
        tool_call: SkillToolCall,
    ) -> SkillToolResult:
        """Runs the skill and returns a contract-valid result (Cenário 5,
        Apêndice H: a malformed result must fail Pydantic validation here,
        before it ever reaches the Quality Gate)."""


class LegacyCodeSkillExecutor(SkillExecutor):
    """Reference PoC executor for the "Código Legado" Agent Skill.

    Reuses the existing RAG-integrated LLM planning call (app.services.llm_service)
    as the retrieval+generation step of its own pipeline, then reshapes the result
    into the resposta_especialista_schema contract instead of duplicating the
    sanitization/hashing/tracing machinery already implemented there.
    """

    def execute(
        self,
        db: Session,
        *,
        skill: AgentSkill,
        technical_request: TechnicalRequest,
        user: User,
        tool_call: SkillToolCall,
    ) -> SkillToolResult:
        plan_response = generate_technical_plan(db, technical_request=technical_request, user=user)

        retrieved_chunks: list[KnowledgeChunk] = []
        llm_invocation = db.scalar(
            select(LLMInvocation).where(LLMInvocation.llm_call_id == plan_response.llm_call_id)
        )
        if llm_invocation and llm_invocation.retrieved_chunk_ids:
            retrieved_chunks = list(
                db.scalars(
                    select(KnowledgeChunk).where(
                        KnowledgeChunk.id.in_(llm_invocation.retrieved_chunk_ids)
                    )
                )
            )

        findings = [
            AchadoTecnico(
                item_identificado=chunk.artifact_name,
                descricao_detalhada=(
                    "Trecho recuperado da base de conhecimento como evidência relevante "
                    "para a análise solicitada."
                ),
                trecho_referenciado=chunk.content[:500],
            )
            for chunk in retrieved_chunks
        ]

        missing = plan_response.plan.missing_information
        if not missing and findings:
            confidence: ConfidenceLevel = "ALTO"
            justification = (
                f"{len(findings)} trecho(s) de evidência recuperados e nenhuma lacuna "
                "de informação identificada pelo planejador técnico."
            )
        elif findings:
            confidence = "MEDIO"
            justification = (
                f"{len(findings)} trecho(s) de evidência recuperados, mas o planejador "
                f"técnico identificou {len(missing)} lacuna(s) de informação."
            )
        else:
            confidence = "BAIXO"
            justification = (
                "Nenhum trecho relevante foi recuperado da base de conhecimento; "
                "a análise carece de evidência documental direta."
            )

        return SkillToolResult(
            trace_id=technical_request.trace_id,
            agente_emissor=AgenteEmissor(
                nome=skill.name,
                versao_prompt=skill.version,
                dominio=skill.domain,
            ),
            analise_estruturada=AnaliseEstruturada(
                resumo_executivo=plan_response.plan.summary,
                descobertas_tecnicas=findings,
                impactos_mapeados=plan_response.plan.risks,
            ),
            governanca=Governanca(
                nivel_confianca=confidence,
                justificativa_confianca=justification,
                referencias_catalogo=[],
            ),
        )


class BusinessRulesSkillExecutor(SkillExecutor):
    """Reference PoC executor for the "Regras de Negócio" Agent Skill.

    Same retrieval+generation pipeline as LegacyCodeSkillExecutor (reuses
    app.services.llm_service instead of duplicating it), reframed around
    business-rule evidence rather than raw code/dependency evidence — the
    distinction between skills in this PoC is domain framing and contract
    metadata, not separate infrastructure.
    """

    def execute(
        self,
        db: Session,
        *,
        skill: AgentSkill,
        technical_request: TechnicalRequest,
        user: User,
        tool_call: SkillToolCall,
    ) -> SkillToolResult:
        plan_response = generate_technical_plan(db, technical_request=technical_request, user=user)

        retrieved_chunks: list[KnowledgeChunk] = []
        llm_invocation = db.scalar(
            select(LLMInvocation).where(LLMInvocation.llm_call_id == plan_response.llm_call_id)
        )
        if llm_invocation and llm_invocation.retrieved_chunk_ids:
            retrieved_chunks = list(
                db.scalars(
                    select(KnowledgeChunk).where(
                        KnowledgeChunk.id.in_(llm_invocation.retrieved_chunk_ids)
                    )
                )
            )

        findings = [
            AchadoTecnico(
                item_identificado=chunk.artifact_name,
                descricao_detalhada=(
                    "Trecho recuperado da base de conhecimento como evidência de regra de "
                    "negócio potencialmente impactada pela mudança solicitada."
                ),
                trecho_referenciado=chunk.content[:500],
            )
            for chunk in retrieved_chunks
        ]

        missing = plan_response.plan.missing_information
        if not missing and findings:
            confidence: ConfidenceLevel = "ALTO"
            justification = (
                f"{len(findings)} trecho(s) de regra de negócio recuperados e nenhuma lacuna "
                "de informação identificada pelo planejador técnico."
            )
        elif findings:
            confidence = "MEDIO"
            justification = (
                f"{len(findings)} trecho(s) de regra de negócio recuperados, mas o planejador "
                f"técnico identificou {len(missing)} lacuna(s) de informação."
            )
        else:
            confidence = "BAIXO"
            justification = (
                "Nenhum trecho relevante foi recuperado da base de conhecimento; a análise de "
                "regras de negócio carece de evidência documental direta."
            )

        return SkillToolResult(
            trace_id=technical_request.trace_id,
            agente_emissor=AgenteEmissor(
                nome=skill.name,
                versao_prompt=skill.version,
                dominio=skill.domain,
            ),
            analise_estruturada=AnaliseEstruturada(
                resumo_executivo=plan_response.plan.summary,
                descobertas_tecnicas=findings,
                impactos_mapeados=plan_response.plan.risks,
            ),
            governanca=Governanca(
                nivel_confianca=confidence,
                justificativa_confianca=justification,
                referencias_catalogo=[],
            ),
        )


class ArchitectureSkillExecutor(SkillExecutor):
    """Reference PoC executor for the "Arquitetura de Software" Agent Skill.

    Same retrieval+generation pipeline as LegacyCodeSkillExecutor, reframed
    around architectural impact evidence (coupling, boundaries, structural
    risk) instead of raw code/dependency evidence.
    """

    def execute(
        self,
        db: Session,
        *,
        skill: AgentSkill,
        technical_request: TechnicalRequest,
        user: User,
        tool_call: SkillToolCall,
    ) -> SkillToolResult:
        plan_response = generate_technical_plan(db, technical_request=technical_request, user=user)

        retrieved_chunks: list[KnowledgeChunk] = []
        llm_invocation = db.scalar(
            select(LLMInvocation).where(LLMInvocation.llm_call_id == plan_response.llm_call_id)
        )
        if llm_invocation and llm_invocation.retrieved_chunk_ids:
            retrieved_chunks = list(
                db.scalars(
                    select(KnowledgeChunk).where(
                        KnowledgeChunk.id.in_(llm_invocation.retrieved_chunk_ids)
                    )
                )
            )

        findings = [
            AchadoTecnico(
                item_identificado=chunk.artifact_name,
                descricao_detalhada=(
                    "Trecho recuperado da base de conhecimento como evidência de impacto "
                    "arquitetural (acoplamento, limites de módulo ou risco estrutural)."
                ),
                trecho_referenciado=chunk.content[:500],
            )
            for chunk in retrieved_chunks
        ]

        missing = plan_response.plan.missing_information
        if not missing and findings:
            confidence: ConfidenceLevel = "ALTO"
            justification = (
                f"{len(findings)} trecho(s) de evidência arquitetural recuperados e nenhuma "
                "lacuna de informação identificada pelo planejador técnico."
            )
        elif findings:
            confidence = "MEDIO"
            justification = (
                f"{len(findings)} trecho(s) de evidência arquitetural recuperados, mas o "
                f"planejador técnico identificou {len(missing)} lacuna(s) de informação."
            )
        else:
            confidence = "BAIXO"
            justification = (
                "Nenhum trecho relevante foi recuperado da base de conhecimento; a análise "
                "arquitetural carece de evidência documental direta."
            )

        return SkillToolResult(
            trace_id=technical_request.trace_id,
            agente_emissor=AgenteEmissor(
                nome=skill.name,
                versao_prompt=skill.version,
                dominio=skill.domain,
            ),
            analise_estruturada=AnaliseEstruturada(
                resumo_executivo=plan_response.plan.summary,
                descobertas_tecnicas=findings,
                impactos_mapeados=plan_response.plan.risks,
            ),
            governanca=Governanca(
                nivel_confianca=confidence,
                justificativa_confianca=justification,
                referencias_catalogo=[],
            ),
        )
