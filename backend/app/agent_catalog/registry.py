from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent_manifest.manifest import AgentSkillManifest
from app.agent_manifest.validator import validate_manifest
from app.core.security import utc_now
from app.models import AgentSkill, User


class AgentSkillValidationError(ValueError):
    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


class AgentSkillNotFoundError(LookupError):
    pass


def register_skill(
    db: Session,
    *,
    manifest: AgentSkillManifest,
    submitted_by: User,
    raw_markdown: str | None = None,
) -> AgentSkill:
    """Registers a new Agent Skill (RF01/RF02/RF04).

    Only registers the skill if the manifest passes governance validation
    (RF03/RFC §6.4); otherwise raises AgentSkillValidationError with the full
    list of problems, so an invalid import (Cenário 2, Apêndice H) can report
    everything wrong at once instead of failing on the first field.
    """
    result = validate_manifest(manifest)
    if not result.is_valid:
        raise AgentSkillValidationError(result.errors)

    now = utc_now()
    skill = AgentSkill(
        name=manifest.name,
        version=manifest.version,
        domain=manifest.domain,
        status="approved",
        enabled=True,
        author_origin=manifest.author_origin,
        objective=manifest.objective,
        manifest_markdown=raw_markdown,
        manifest_json=manifest.model_dump(mode="json"),
        input_contract_ref=manifest.input_contract_ref,
        output_contract_ref=manifest.output_contract_ref,
        uses_external_services=manifest.uses_external_services,
        submitted_by_id=submitted_by.id,
        validated_at=now,
    )
    db.add(skill)
    db.flush()
    return skill


def get_skill(db: Session, skill_id: str) -> AgentSkill:
    skill = db.get(AgentSkill, skill_id)
    if skill is None:
        raise AgentSkillNotFoundError(f"Agent Skill '{skill_id}' não encontrada.")
    return skill


def list_active_skills(db: Session) -> list[AgentSkill]:
    return list(
        db.scalars(
            select(AgentSkill)
            .where(AgentSkill.status == "approved", AgentSkill.enabled.is_(True))
            .order_by(AgentSkill.name)
        )
    )


def list_all_skills(db: Session) -> list[AgentSkill]:
    return list(db.scalars(select(AgentSkill).order_by(AgentSkill.created_at.desc())))


def select_skills_for_domain(db: Session, *, domain: str) -> list[AgentSkill]:
    """Selects skills compatible with a domain (RF09).

    Deliberately an exact-match filter on the declared domain rather than
    semantic/NLP matching: cheaper, deterministic, and easy to demonstrate/
    test — appropriate for a solo-developer PoC (Documento de referência's
    Orquestrador aspirations are explicitly out of scope here).
    """
    return list(
        db.scalars(
            select(AgentSkill)
            .where(
                AgentSkill.domain == domain,
                AgentSkill.status == "approved",
                AgentSkill.enabled.is_(True),
            )
            .order_by(AgentSkill.name)
        )
    )


def enable_skill(db: Session, skill_id: str) -> AgentSkill:
    skill = get_skill(db, skill_id)
    skill.enabled = True
    db.flush()
    return skill


def disable_skill(db: Session, skill_id: str) -> AgentSkill:
    skill = get_skill(db, skill_id)
    skill.enabled = False
    db.flush()
    return skill
