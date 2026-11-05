"""Motor de sugestão: há alguma Agent Skill que ajudaria e ainda não está no clã?

Compara o embedding da solicitação com o de cada skill ativa por similaridade de
cosseno. Só usa o modelo de embeddings, nunca o de chat, e o vetor de cada skill fica
guardado até o texto dela mudar. O resultado é só uma sugestão: quem decide adicionar
a skill é a pessoa.

Não é um modelo treinado: não há exemplos rotulados de "solicitação e skill certa"
para isso. A qualidade é medida em tests/test_skill_suggestion_quality.py.
"""

import logging
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.agent_catalog.registry import list_active_skills, list_clan_skills
from app.agent_manifest.manifest import DOMAIN_LABELS
from app.core.config import Settings, settings
from app.llm.security import content_sha256, sanitize_content
from app.models import AgentSkill
from app.rag.base import EmbeddingProvider
from app.rag.factory import RAGConfigurationError, create_embedding_provider
from app.rag.retriever import cosine_similarity

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SkillSuggestion:
    skill: AgentSkill
    score: float


@dataclass(frozen=True)
class SuggestionResult:
    available: bool
    suggestions: list[SkillSuggestion]
    best_clan_score: float | None
    covered_by_clan: bool
    catalog_gap: bool


UNAVAILABLE = SuggestionResult(
    available=False, suggestions=[], best_clan_score=None, covered_by_clan=False, catalog_gap=False
)


def _skill_text(skill: AgentSkill) -> str:
    manifest = skill.manifest_json or {}
    parts = [
        skill.name,
        f"Área: {DOMAIN_LABELS.get(skill.domain, skill.domain)}",
        skill.objective,
        *manifest.get("capabilities", []),
    ]
    return "\n".join(part for part in parts if part)


def _ensure_skill_embeddings(db: Session, skills: list[AgentSkill], provider: EmbeddingProvider) -> None:
    texts = {skill.id: _skill_text(skill) for skill in skills}
    stale = [
        skill
        for skill in skills
        if skill.embedding is None or skill.embedding_text_hash != content_sha256(texts[skill.id])
    ]
    if not stale:
        return

    vectors = provider.embed([texts[skill.id] for skill in stale])
    for skill, vector in zip(stale, vectors, strict=True):
        skill.embedding = vector
        skill.embedding_text_hash = content_sha256(texts[skill.id])
    db.commit()


def suggest_skills(
    db: Session,
    *,
    clan_id: str,
    viewer_id: str,
    query_parts: list[str | None],
    config: Settings = settings,
) -> SuggestionResult:
    query = sanitize_content(
        "\n".join(part for part in query_parts if part),
        max_chars=config.llm_max_input_chars,
        redact=True,
    ).value

    clan_skills = list_clan_skills(db, clan_id=clan_id, only_active=True)
    clan_ids = {skill.id for skill in clan_skills}
    others = [skill for skill in list_active_skills(db, viewer_id=viewer_id) if skill.id not in clan_ids]

    # Sem isso a orquestração continua funcionando: a falha só deixa o motor indisponível.
    try:
        provider = create_embedding_provider(config)
        query_vector = provider.embed([query])[0]
        _ensure_skill_embeddings(db, clan_skills + others, provider)
    except RAGConfigurationError:
        return UNAVAILABLE
    except Exception:  # noqa: BLE001 - provedor externo: qualquer falha vira "indisponível"
        db.rollback()
        logger.exception("Falha ao gerar embeddings para a sugestão de Agent Skills")
        return UNAVAILABLE

    def score_of(skill: AgentSkill) -> float:
        return cosine_similarity(query_vector, skill.embedding or [])

    min_score = config.skill_suggestion_min_score
    clan_scores = [score_of(skill) for skill in clan_skills]
    best_clan_score = max(clan_scores) if clan_scores else None
    scored = sorted(
        (SkillSuggestion(skill=skill, score=score_of(skill)) for skill in others),
        key=lambda item: item.score,
        reverse=True,
    )
    suggestions = [item for item in scored if item.score >= min_score][: config.skill_suggestion_max_results]
    covered_by_clan = best_clan_score is not None and best_clan_score >= min_score

    return SuggestionResult(
        available=True,
        suggestions=suggestions,
        best_clan_score=best_clan_score,
        covered_by_clan=covered_by_clan,
        catalog_gap=not suggestions and not covered_by_clan,
    )
