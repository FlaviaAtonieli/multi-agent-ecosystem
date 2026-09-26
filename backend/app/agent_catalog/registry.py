from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agent_manifest.manifest import AgentSkillManifest
from app.agent_manifest.validator import validate_manifest
from app.core.security import utc_now
from app.models import AgentSkill, AgentSkillInvocation, ClanMembership, User


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
    owner_id: str | None = None,
    visibility: str = "OFFICIAL",
    clan_id: str | None = None,
) -> AgentSkill:
    """Registers a new Agent Skill (RF01/RF02/RF04).

    Only registers the skill if the manifest passes governance validation
    (RF03/RFC §6.4); otherwise raises AgentSkillValidationError with the full
    list of problems, so an invalid import (Cenário 2, Apêndice H) can report
    everything wrong at once instead of failing on the first field.

    visibility defaults to OFFICIAL (visible/executable by every authenticated
    user, not just its owner) -- otherwise the catalog would stay empty for
    everyone except whichever TECHNICIAN/ADMIN happened to import each skill,
    and a plain USER (allowed to execute orchestrations, see
    ORCHESTRATION_ROLES in app/core/roles.py) would have nothing to run.
    owner_id is still recorded for attribution/audit; pass visibility="PRIVATE"
    explicitly for a skill still being drafted/tested that shouldn't be
    executable by anyone but its owner (and ADMIN) yet, or visibility="CLAN"
    with clan_id set for a skill scoped to a specific clan's members.
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
        owner_id=owner_id,
        visibility=visibility,
        clan_id=clan_id,
        persona_instructions=manifest.persona_instructions,
    )
    db.add(skill)
    db.flush()
    return skill


def get_skill(db: Session, skill_id: str) -> AgentSkill:
    skill = db.get(AgentSkill, skill_id)
    if skill is None:
        raise AgentSkillNotFoundError(f"Agent Skill '{skill_id}' não encontrada.")
    return skill


def _visibility_filter(viewer_id: str | None):
    """Um usuário enxerga skills OFFICIAL (o padrão para toda skill nova, ver
    register_skill), as que ele mesmo criou como PRIVATE (nunca a de outro
    usuário), e as CLAN de qualquer clã do qual ele seja membro. Seguro por
    padrão: sem viewer_id, só as oficiais aparecem (nunca vaza skill privada
    nem de clã de ninguém)."""
    if viewer_id is None:
        return AgentSkill.visibility == "OFFICIAL"
    member_clan_ids = select(ClanMembership.clan_id).where(ClanMembership.user_id == viewer_id)
    return (
        (AgentSkill.visibility == "OFFICIAL")
        | (AgentSkill.owner_id == viewer_id)
        | ((AgentSkill.visibility == "CLAN") & AgentSkill.clan_id.in_(member_clan_ids))
    )


def list_active_skills(db: Session, *, viewer_id: str | None = None) -> list[AgentSkill]:
    return list(
        db.scalars(
            select(AgentSkill)
            .where(
                AgentSkill.status == "approved",
                AgentSkill.enabled.is_(True),
                _visibility_filter(viewer_id),
            )
            .order_by(AgentSkill.name)
        )
    )


def list_all_skills(db: Session, *, viewer_id: str | None = None) -> list[AgentSkill]:
    """Like list_active_skills but includes pending/disabled skills too (admin
    catalog management). Still owner-scoped: a non-official skill only shows
    up here for its own owner, same rule as everywhere else in the catalog."""
    return list(
        db.scalars(
            select(AgentSkill)
            .where(_visibility_filter(viewer_id))
            .order_by(AgentSkill.created_at.desc())
        )
    )


def select_skills_for_domain(
    db: Session, *, domain: str, viewer_id: str | None = None
) -> list[AgentSkill]:
    """Selects skills compatible with a domain (RF09).

    Deliberately an exact-match filter on the declared domain rather than
    semantic/NLP matching: cheaper, deterministic, and easy to demonstrate/
    test — appropriate for a solo-developer PoC (Documento de referência's
    Orquestrador aspirations are explicitly out of scope here).

    viewer_id scopes the result to official skills plus that user's own
    (fase 1 da rede de agentes) — never another user's private skill, even if
    it happens to share the same domain as an official one.
    """
    return list(
        db.scalars(
            select(AgentSkill)
            .where(
                AgentSkill.domain == domain,
                AgentSkill.status == "approved",
                AgentSkill.enabled.is_(True),
                _visibility_filter(viewer_id),
            )
            .order_by(AgentSkill.name)
        )
    )


def official_skill_usage_ranking(db: Session, *, limit: int = 5) -> list[tuple[AgentSkill, int]]:
    """Ranks OFFICIAL skills by successful invocation count, all-time.

    Restricted to OFFICIAL (never PRIVATE) since this powers a public "most used"
    surface in the catalog -- showing usage counts for someone else's private skill
    would leak activity information about it. Only status == COMPLETED counts:
    a skill that gets invoked a lot but keeps failing shouldn't rank as "popular".
    """
    usage_count = func.count(AgentSkillInvocation.id).label("usage_count")
    rows = db.execute(
        select(AgentSkill, usage_count)
        .join(AgentSkillInvocation, AgentSkillInvocation.agent_skill_id == AgentSkill.id)
        .where(AgentSkill.visibility == "OFFICIAL", AgentSkillInvocation.status == "COMPLETED")
        .group_by(AgentSkill.id)
        .order_by(usage_count.desc())
        .limit(limit)
    ).all()
    return [(row[0], row[1]) for row in rows]


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
