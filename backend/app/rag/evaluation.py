from pydantic import BaseModel


class RetrievalEvalCase(BaseModel):
    """A query with its known-relevant source artifacts, for measuring retrieval
    quality against a real (not synthetic-random) ground truth."""

    query: str
    relevant_artifacts: set[str]


def _ranked_artifacts(retrieved_artifacts: list[str]) -> list[str]:
    """Collapses repeated artifact names to their first (highest-ranked) occurrence.

    A single file yields several chunks, so the raw retrieval list can contain the
    same artifact more than once; precision/recall are defined over distinct
    documents, not chunks.
    """
    seen: list[str] = []
    for name in retrieved_artifacts:
        if name not in seen:
            seen.append(name)
    return seen


def precision_at_k(retrieved_artifacts: list[str], relevant_artifacts: set[str], k: int) -> float:
    ranked = _ranked_artifacts(retrieved_artifacts)[:k]
    if not ranked:
        return 0.0
    hits = sum(1 for name in ranked if name in relevant_artifacts)
    return hits / len(ranked)


def recall_at_k(retrieved_artifacts: list[str], relevant_artifacts: set[str], k: int) -> float:
    if not relevant_artifacts:
        return 0.0
    ranked = set(_ranked_artifacts(retrieved_artifacts)[:k])
    hits = sum(1 for name in relevant_artifacts if name in ranked)
    return hits / len(relevant_artifacts)


def reciprocal_rank(retrieved_artifacts: list[str], relevant_artifacts: set[str]) -> float:
    for position, name in enumerate(_ranked_artifacts(retrieved_artifacts), start=1):
        if name in relevant_artifacts:
            return 1 / position
    return 0.0


# Ground truth grounded in the real fixture content under
# app/rag/fixtures/legacy_billing/ (the only domain with a populated knowledge
# base today -- see docs/validation/evidence/2026-08-30-rag-quality-validation.md
# for why the other three Agent Skill domains are out of scope for this measurement).
LEGACY_BILLING_GROUND_TRUTH: list[RetrievalEvalCase] = [
    RetrievalEvalCase(
        query="Qual é o valor do limite de crédito hoje e em qual classe ele está definido?",
        relevant_artifacts={"CreditLimitService.java", "business-rules.md"},
    ),
    RetrievalEvalCase(
        query="O campo SEGMENTO do cliente é considerado no cálculo do limite de crédito?",
        relevant_artifacts={
            "CreditLimitService.java",
            "CustomerRepository.java",
            "business-rules.md",
            "schema.sql",
        },
    ),
    RetrievalEvalCase(
        query=(
            "Quais pontos do sistema dependem do limite de crédito atual e "
            "precisam ser atualizados se a regra mudar?"
        ),
        relevant_artifacts={"business-rules.md", "CreditLimitService.java"},
    ),
    RetrievalEvalCase(
        query="Como o repositório calcula o total de pedidos em aberto de um cliente?",
        relevant_artifacts={"CustomerRepository.java"},
    ),
    RetrievalEvalCase(
        query="Existe uma tabela no banco de dados dedicada ao limite de crédito por segmento?",
        relevant_artifacts={"schema.sql"},
    ),
    RetrievalEvalCase(
        query="Quais são os valores possíveis do campo SEGMENTO na tabela CUSTOMER?",
        relevant_artifacts={"schema.sql"},
    ),
    RetrievalEvalCase(
        query="O CustomerRepository usa algum ORM para acessar o banco de dados?",
        relevant_artifacts={"CustomerRepository.java"},
    ),
    RetrievalEvalCase(
        query="Qual método decide se um pedido pode ser aprovado com base no limite disponível do cliente?",
        relevant_artifacts={"CreditLimitService.java"},
    ),
]
