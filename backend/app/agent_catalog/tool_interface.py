from abc import ABC, abstractmethod

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent_catalog.contracts import (
    AchadoTecnico,
    AgenteEmissor,
    AnaliseEstruturada,
    ConfidenceLevel,
    Governanca,
    SkillToolCall,
    SkillToolDescriptor,
    SkillToolResult,
    list_tools,
)
from app.agent_manifest.manifest import DOMAIN_LABELS
from app.models import AgentSkill, KnowledgeChunk, LLMInvocation, TechnicalRequest, User
from app.services.llm_service import generate_technical_plan

__all__ = [
    "AchadoTecnico",
    "AgenteEmissor",
    "AnaliseEstruturada",
    "ConfidenceLevel",
    "Governanca",
    "SkillToolCall",
    "SkillToolDescriptor",
    "SkillToolResult",
    "list_tools",
    "SkillExecutor",
    "LegacyCodeSkillExecutor",
    "BusinessRulesSkillExecutor",
    "ArchitectureSkillExecutor",
    "SecuritySkillExecutor",
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
        plan_response = generate_technical_plan(
            db,
            technical_request=technical_request,
            user=user,
            requested_model=tool_call.requested_model,
            analysis_domain_label=DOMAIN_LABELS.get(skill.domain),
        )

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
        plan_response = generate_technical_plan(
            db,
            technical_request=technical_request,
            user=user,
            requested_model=tool_call.requested_model,
            analysis_domain_label=DOMAIN_LABELS.get(skill.domain),
        )

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
        plan_response = generate_technical_plan(
            db,
            technical_request=technical_request,
            user=user,
            requested_model=tool_call.requested_model,
            analysis_domain_label=DOMAIN_LABELS.get(skill.domain),
        )

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


class SecuritySkillExecutor(SkillExecutor):
    """Reference PoC executor for the "Segurança da Informação" Agent Skill.

    Added after the other three, as evidence for RFC §5.5 criterio 7 (prova de
    extensibilidade plug-and-play): same retrieval+generation pipeline as
    LegacyCodeSkillExecutor, reframed around security-impact evidence (data
    exposure, access control, injection surface) instead of raw code/dependency
    evidence. Nothing in the Orquestrador itself changed to accommodate this.
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
        plan_response = generate_technical_plan(
            db,
            technical_request=technical_request,
            user=user,
            requested_model=tool_call.requested_model,
            analysis_domain_label=DOMAIN_LABELS.get(skill.domain),
        )

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
                    "Trecho recuperado da base de conhecimento como evidência de risco de "
                    "segurança (exposição de dados, controle de acesso ou superfície de injeção)."
                ),
                trecho_referenciado=chunk.content[:500],
            )
            for chunk in retrieved_chunks
        ]

        missing = plan_response.plan.missing_information
        if not missing and findings:
            confidence: ConfidenceLevel = "ALTO"
            justification = (
                f"{len(findings)} trecho(s) de evidência de segurança recuperados e nenhuma "
                "lacuna de informação identificada pelo planejador técnico."
            )
        elif findings:
            confidence = "MEDIO"
            justification = (
                f"{len(findings)} trecho(s) de evidência de segurança recuperados, mas o "
                f"planejador técnico identificou {len(missing)} lacuna(s) de informação."
            )
        else:
            confidence = "BAIXO"
            justification = (
                "Nenhum trecho relevante foi recuperado da base de conhecimento; a análise "
                "de segurança carece de evidência documental direta."
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
