import re
from itertools import combinations

from pydantic import BaseModel, Field

from app.agent_catalog.tool_interface import SkillToolResult


class QualityGateVerdict(BaseModel):
    approved: bool
    requires_human_review: bool
    reasons: list[str] = Field(default_factory=list)
    # Com relator: quanto do parecer de cada agente o parecer final considerou (0 a 1).
    relator_coverage: dict[str, float] | None = None


# Abaixo disso, o parecer final é tratado como se tivesse ignorado o agente. Valor inicial,
# a recalibrar com as avaliações 👍/👎 das respostas do relator.
RELATOR_MIN_COVERAGE = 0.2

_TERM = re.compile(r"\w+")


def _terms(text: str) -> set[str]:
    return {term for term in _TERM.findall(text.lower()) if len(term) > 3}


def _key_terms(result: SkillToolResult) -> set[str]:
    analysis = result.analise_estruturada
    items = [finding.item_identificado for finding in analysis.descobertas_tecnicas]
    return _terms(" ".join([analysis.resumo_executivo, *items]))


def _all_terms(result: SkillToolResult) -> set[str]:
    analysis = result.analise_estruturada
    parts = [analysis.resumo_executivo, *analysis.impactos_mapeados]
    for finding in analysis.descobertas_tecnicas:
        parts += [finding.item_identificado, finding.descricao_detalhada]
    return _terms(" ".join(parts))


def relator_coverage(relator: SkillToolResult, others: list[SkillToolResult]) -> dict[str, float]:
    """Para cada agente, a fração dos termos do resumo e dos achados dele que aparece no
    parecer do relator. Mede se o relator considerou o agente, não se concorda com ele."""
    relator_terms = _all_terms(relator)
    coverage: dict[str, float] = {}
    for other in others:
        terms = _key_terms(other)
        coverage[other.agente_emissor.nome] = (
            round(len(terms & relator_terms) / len(terms), 2) if terms else 1.0
        )
    return coverage


def _word_set(text: str) -> set[str]:
    return {word for word in text.lower().split() if len(word) > 3}


def _jaccard_similarity(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    intersection = len(a & b)
    union = len(a | b)
    return intersection / union if union else 0.0


def evaluate(
    results: list[SkillToolResult],
    *,
    files_requested: bool = False,
    files_delivered: bool | None = None,
    package_issues: list[str] | None = None,
    relator_names: set[str] | None = None,
) -> QualityGateVerdict:
    """Confere as respostas das skills antes da entrega (RF11).

    As regras são explícitas e explicáveis, sem um segundo LLM como juiz: a avaliação
    fica reproduzível e barata de testar.
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

    # O modelo às vezes ignora o pedido de arquivos (ver app/llm/file_request.py).
    # Na orquestração, o conteúdo dos arquivos sai da resposta depois de guardado
    # (skill_artifacts): quem chama informa se algum arquivo foi guardado.
    if files_delivered is None:
        files_delivered = any(result.arquivos for result in results)
    missing_files = files_requested and not files_delivered
    if missing_files:
        reasons.append("A solicitação pediu arquivos, mas nenhuma Agent Skill os gerou.")

    # Checagem sem IA do pacote entregue (app/services/artifact_service.check_package).
    if package_issues:
        reasons.append("Pacote de arquivos incompleto: " + " ".join(package_issues))

    coverage, uncovered = _relator_check(results, relator_names or set(), reasons)

    approved = not low_confidence and not divergent_pairs
    requires_human_review = (
        not approved
        or bool(medium_confidence)
        or missing_files
        or bool(package_issues)
        or bool(uncovered)
    )

    if approved and not reasons:
        reasons.append("Todas as respostas passaram na validação de contrato e confiança.")

    return QualityGateVerdict(
        approved=approved,
        requires_human_review=requires_human_review,
        reasons=reasons,
        relator_coverage=coverage,
    )


def _relator_check(
    results: list[SkillToolResult], relator_names: set[str], reasons: list[str]
) -> tuple[dict[str, float] | None, list[str]]:
    """Cobertura do parecer final sobre cada agente. Com mais de um relator, vale a menor."""
    relators = [r for r in results if r.agente_emissor.nome in relator_names]
    others = [r for r in results if r.agente_emissor.nome not in relator_names]
    if not relators or not others:
        return None, []
    coverage: dict[str, float] = {}
    for relator in relators:
        for name, value in relator_coverage(relator, others).items():
            coverage[name] = min(value, coverage.get(name, value))
    uncovered = [name for name, value in coverage.items() if value < RELATOR_MIN_COVERAGE]
    if uncovered:
        reasons.append(
            "O parecer final não considera: "
            + ", ".join(f"{name} (cobertura {coverage[name]:.2f})" for name in uncovered)
            + "."
        )
    else:
        average = sum(coverage.values()) / len(coverage)
        reasons.append(f"O parecer final considera todos os agentes (cobertura média {average:.2f}).")
    return coverage, uncovered
