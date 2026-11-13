"""Executor único das Agent Skills: planejamento com RAG e resposta no contrato do especialista.

Toda skill, oficial ou criada por alguém, passa por aqui. O que muda de uma área
para outra são as instruções da skill (persona) e as frases sobre a evidência.
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent_catalog.contracts import (
    AchadoTecnico,
    AgenteEmissor,
    AnaliseEstruturada,
    ArquivoGerado,
    ConfidenceLevel,
    Governanca,
    SkillToolCall,
    SkillToolDescriptor,
    SkillToolResult,
    list_tools,
)
from app.agent_manifest.manifest import DOMAIN_LABELS
from app.llm.schemas import LLMPlan
from app.models import AgentSkill, KnowledgeChunk, LLMInvocation, TechnicalRequest, User
from app.services.llm_service import generate_technical_plan

__all__ = [
    "AchadoTecnico",
    "AgenteEmissor",
    "AnaliseEstruturada",
    "ConfidenceLevel",
    "Governanca",
    "SkillExecutor",
    "SkillToolCall",
    "SkillToolDescriptor",
    "SkillToolResult",
    "evidence_wording",
    "list_tools",
]


@dataclass(frozen=True)
class EvidenceWording:
    """Como a resposta descreve a evidência recuperada, na linguagem da área."""

    finding: str
    evidence: str  # "de evidência", "de regra de negócio"...
    analysis: str  # "a análise", "a análise de segurança"...

    def found(self, chunks: int) -> str:
        return (
            f"{chunks} trecho(s) {self.evidence} recuperados e nenhuma lacuna de informação "
            "identificada pelo planejador técnico."
        )

    def partial(self, chunks: int, gaps: int) -> str:
        return (
            f"{chunks} trecho(s) {self.evidence} recuperados, mas o planejador técnico identificou "
            f"{gaps} lacuna(s) de informação."
        )

    @property
    def nothing(self) -> str:
        return (
            "Nenhum trecho relevante foi recuperado da base de conhecimento; "
            f"{self.analysis} carece de evidência documental direta."
        )


_GENERAL = EvidenceWording(
    finding="Trecho recuperado da base de conhecimento como evidência relevante para a análise solicitada.",
    evidence="de evidência",
    analysis="a análise",
)
_BY_DOMAIN = {
    "regras_negocio": EvidenceWording(
        finding="Trecho recuperado da base de conhecimento como evidência de regra de negócio "
        "potencialmente impactada pela mudança solicitada.",
        evidence="de regra de negócio",
        analysis="a análise de regras de negócio",
    ),
    "arquitetura_software": EvidenceWording(
        finding="Trecho recuperado da base de conhecimento como evidência de impacto arquitetural "
        "(acoplamento, limites de módulo ou risco estrutural).",
        evidence="de evidência arquitetural",
        analysis="a análise arquitetural",
    ),
    "seguranca_informacao": EvidenceWording(
        finding="Trecho recuperado da base de conhecimento como evidência de risco de segurança "
        "(exposição de dados, controle de acesso ou superfície de injeção).",
        evidence="de evidência de segurança",
        analysis="a análise de segurança",
    ),
}


def evidence_wording(domain: str) -> EvidenceWording:
    return _BY_DOMAIN.get(domain, _GENERAL)


def _generated_files(plan: LLMPlan) -> list[ArquivoGerado]:
    return [ArquivoGerado(nome=file.filename, conteudo=file.content) for file in plan.generated_files]


def _retrieved_chunks(db: Session, llm_call_id: str) -> list[KnowledgeChunk]:
    invocation = db.scalar(select(LLMInvocation).where(LLMInvocation.llm_call_id == llm_call_id))
    if not invocation or not invocation.retrieved_chunk_ids:
        return []
    return list(
        db.scalars(select(KnowledgeChunk).where(KnowledgeChunk.id.in_(invocation.retrieved_chunk_ids)))
    )


class SkillExecutor:
    def execute(
        self,
        db: Session,
        *,
        skill: AgentSkill,
        technical_request: TechnicalRequest,
        user: User,
        tool_call: SkillToolCall,
    ) -> SkillToolResult:
        """Um resultado fora do contrato falha na validação do Pydantic aqui, antes de chegar
        ao Quality Gate (cenário 5 do Apêndice H da RFC)."""
        plan_response = generate_technical_plan(
            db,
            technical_request=technical_request,
            user=user,
            requested_model=tool_call.requested_model,
            analysis_domain_label=DOMAIN_LABELS.get(skill.domain, skill.domain),
            additional_question=tool_call.additional_question,
            team_context=tool_call.team_context,
            persona_instructions=skill.persona_instructions,
        )
        wording = evidence_wording(skill.domain)
        findings = [
            AchadoTecnico(
                item_identificado=chunk.artifact_name,
                descricao_detalhada=wording.finding,
                trecho_referenciado=chunk.content[:500],
            )
            for chunk in _retrieved_chunks(db, plan_response.llm_call_id)
        ]

        # A confiança mede evidência documental: sem trechos da base, é BAIXA.
        missing = plan_response.plan.missing_information
        confidence: ConfidenceLevel
        if findings and not missing:
            confidence, justification = "ALTO", wording.found(len(findings))
        elif findings:
            confidence, justification = "MEDIO", wording.partial(len(findings), len(missing))
        else:
            confidence, justification = "BAIXO", wording.nothing

        return SkillToolResult(
            trace_id=technical_request.trace_id,
            agente_emissor=AgenteEmissor(nome=skill.name, versao_prompt=skill.version, dominio=skill.domain),
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
            arquivos=_generated_files(plan_response.plan),
        )
