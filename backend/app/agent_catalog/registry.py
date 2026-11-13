from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agent_manifest.manifest import AgentSkillManifest, normalize_domain_key
from app.agent_manifest.validator import validate_manifest
from app.core.security import utc_now
from app.models import AgentSkill, AgentSkillInvocation, ClanMembership, ClanSkill, User


class AgentSkillValidationError(ValueError):
    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


class AgentSkillNotFoundError(LookupError):
    pass


def canonical_domain(db: Session, domain: str) -> str:
    """Reaproveita a grafia já usada no catálogo, para "contabilidade" e "Contabilidade"
    serem a mesma área: a seleção das skills compara o domínio exato.
    """
    key = normalize_domain_key(domain)
    for existing in db.scalars(select(AgentSkill.domain).distinct()):
        if normalize_domain_key(existing) == key:
            return existing
    return domain


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
    """Cadastra uma Agent Skill (RF01, RF02, RF04) se o manifesto passar na governança (RF03).

    Se não passar, AgentSkillValidationError traz todos os problemas de uma vez. A
    visibilidade padrão é OFFICIAL; PRIVATE serve para uma skill ainda em teste, e
    CLAN, com clan_id, para uma skill só dos membros de um comitê.
    """
    result = validate_manifest(manifest)
    if not result.is_valid:
        raise AgentSkillValidationError(result.errors)

    manifest = manifest.model_copy(update={"domain": canonical_domain(db, manifest.domain)})
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
    if clan_id:
        add_skill_to_clan(db, clan_id=clan_id, skill_id=skill.id, added_by_id=submitted_by.id)
    return skill


def add_skill_to_clan(db: Session, *, clan_id: str, skill_id: str, added_by_id: str) -> ClanSkill:
    link = ClanSkill(clan_id=clan_id, agent_skill_id=skill_id, added_by_id=added_by_id)
    db.add(link)
    db.flush()
    return link


def get_clan_skill_link(db: Session, *, clan_id: str, skill_id: str) -> ClanSkill | None:
    return db.scalar(
        select(ClanSkill).where(ClanSkill.clan_id == clan_id, ClanSkill.agent_skill_id == skill_id)
    )


def list_clan_skills(db: Session, *, clan_id: str, only_active: bool = False) -> list[AgentSkill]:
    query = (
        select(AgentSkill)
        .join(ClanSkill, ClanSkill.agent_skill_id == AgentSkill.id)
        .where(ClanSkill.clan_id == clan_id)
        .order_by(AgentSkill.name)
    )
    if only_active:
        query = query.where(AgentSkill.status == "approved", AgentSkill.enabled.is_(True))
    return list(db.scalars(query))


def find_visible_skill(db: Session, *, skill_id: str, viewer_id: str) -> AgentSkill | None:
    return db.scalar(select(AgentSkill).where(AgentSkill.id == skill_id, _visibility_filter(viewer_id)))


def get_skill(db: Session, skill_id: str) -> AgentSkill:
    skill = db.get(AgentSkill, skill_id)
    if skill is None:
        raise AgentSkillNotFoundError(f"Agent Skill '{skill_id}' não encontrada.")
    return skill


def _visibility_filter(viewer_id: str | None):
    """Um usuário enxerga skills OFFICIAL (o padrão para toda skill nova, ver
    register_skill), as que ele mesmo criou como PRIVATE (nunca a de outro
    usuário), e as CLAN de qualquer comitê do qual ele seja membro. Seguro por
    padrão: sem viewer_id, só as oficiais aparecem (nunca vaza skill privada
    nem de comitê de ninguém)."""
    if viewer_id is None:
        return AgentSkill.visibility == "OFFICIAL"
    member_clan_ids = select(ClanMembership.clan_id).where(ClanMembership.user_id == viewer_id)
    shared_with_viewer = select(ClanSkill.agent_skill_id).where(ClanSkill.clan_id.in_(member_clan_ids))
    return (
        (AgentSkill.visibility == "OFFICIAL")
        | (AgentSkill.owner_id == viewer_id)
        | ((AgentSkill.visibility == "CLAN") & AgentSkill.clan_id.in_(member_clan_ids))
        | AgentSkill.id.in_(shared_with_viewer)
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
    """Como list_active_skills, mas inclui as skills pendentes e desativadas. Continua
    restrita ao dono: uma skill não oficial só aparece para quem a criou.
    """
    return list(
        db.scalars(
            select(AgentSkill)
            .where(_visibility_filter(viewer_id))
            .order_by(AgentSkill.created_at.desc())
        )
    )


def official_skill_usage_ranking(db: Session, *, limit: int = 5) -> list[tuple[AgentSkill, int]]:
    """Ranking das skills OFFICIAL por execuções concluídas.

    Só OFFICIAL, porque o ranking é público e mostraria o uso de skills privadas de
    outras pessoas. Só COMPLETED, para uma skill que falha muito não parecer popular.
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


def update_skill(
    db: Session,
    *,
    skill: AgentSkill,
    manifest: AgentSkillManifest,
    visibility: str,
    clan_id: str | None,
) -> AgentSkill:
    """Edita a skill (mesmo id) com a mesma validação do cadastro. O manifest_markdown
    é apagado, porque o conteúdo passa a vir do formulário, não do arquivo importado.
    """
    result = validate_manifest(manifest)
    if not result.is_valid:
        raise AgentSkillValidationError(result.errors)

    manifest = manifest.model_copy(update={"domain": canonical_domain(db, manifest.domain)})
    skill.name = manifest.name
    skill.version = manifest.version
    skill.domain = manifest.domain
    skill.author_origin = manifest.author_origin
    skill.objective = manifest.objective
    skill.manifest_markdown = None
    skill.manifest_json = manifest.model_dump(mode="json")
    skill.input_contract_ref = manifest.input_contract_ref
    skill.output_contract_ref = manifest.output_contract_ref
    skill.uses_external_services = manifest.uses_external_services
    skill.persona_instructions = manifest.persona_instructions
    skill.visibility = visibility
    skill.clan_id = clan_id
    skill.validated_at = utc_now()
    db.flush()
    if clan_id and get_clan_skill_link(db, clan_id=clan_id, skill_id=skill.id) is None:
        add_skill_to_clan(db, clan_id=clan_id, skill_id=skill.id, added_by_id=skill.submitted_by_id)
    return skill
