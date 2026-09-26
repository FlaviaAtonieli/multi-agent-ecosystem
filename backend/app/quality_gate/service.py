from itertools import combinations

from pydantic import BaseModel, Field

from app.agent_catalog.tool_interface import SkillToolResult


class QualityGateVerdict(BaseModel):
    approved: bool
    requires_human_review: bool
    reasons: list[str] = Field(default_factory=list)


def _word_set(text: str) -> set[str]:
    return {word for word in text.lower().split() if len(word) > 3}


def _jaccard_similarity(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    intersection = len(a & b)
    union = len(a | b)
    return intersection / union if union else 0.0


def evaluate(results: list[SkillToolResult]) -> QualityGateVerdict:
    """Cross-checks the consolidated Agent Skill responses before delivery (RF11).

    Rules are explicit and explainable — not a second LLM acting as judge — which
    keeps the PoC's quality evaluation reproducible and cheap to test (aligned with
    RFC §5.5: "validação qualitativa e técnica").
    """
    reasons: list[str] = []

    if not results:
        return QualityGateVerdict(
            approved=False,
            requires_human_review=True,
            reasons=["Nenhuma resposta de Agent Skill foi produzida para consolidação."],
        )

    low_confidence = [r for r in results if r.governanca.nivel_confianca == "BAIXO"]
    medium_confidence = [r for r in results if r.governanca.nivel_confianca == "MEDIO"]
    if low_confidence:
        reasons.append(
            f"{len(low_confidence)} resposta(s) com nível de confiança BAIXO: "
            + ", ".join(r.agente_emissor.nome for r in low_confidence)
        )
    if medium_confidence:
        reasons.append(
            f"{len(medium_confidence)} resposta(s) com nível de confiança MÉDIO: "
            + ", ".join(r.agente_emissor.nome for r in medium_confidence)
        )

    divergent_pairs: list[str] = []
    by_domain: dict[str, list[SkillToolResult]] = {}
    for result in results:
        by_domain.setdefault(result.agente_emissor.dominio, []).append(result)

    for domain, domain_results in by_domain.items():
        for first, second in combinations(domain_results, 2):
            similarity = _jaccard_similarity(
                _word_set(first.analise_estruturada.resumo_executivo),
                _word_set(second.analise_estruturada.resumo_executivo),
            )
            if similarity < 0.1:
                divergent_pairs.append(
                    f"{first.agente_emissor.nome} vs. {second.agente_emissor.nome} (domínio {domain})"
                )

    if divergent_pairs:
        reasons.append(
            "Divergência textual relevante entre respostas do mesmo domínio: "
            + "; ".join(divergent_pairs)
        )

    approved = not low_confidence and not divergent_pairs
    requires_human_review = not approved or bool(medium_confidence)

    if approved and not reasons:
        reasons.append("Todas as respostas passaram na validação de contrato e confiança.")

    return QualityGateVerdict(
        approved=approved,
        requires_human_review=requires_human_review,
        reasons=reasons,
    )
