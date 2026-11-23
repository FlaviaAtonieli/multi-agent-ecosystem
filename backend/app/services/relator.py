"""Relator da plataforma: componente fixo da orquestração, como o orquestrador e o Quality Gate.

Toda orquestração com dois ou mais agentes fecha com um parecer final escrito a partir
dos pareceres de todos. Um comitê pode ter o próprio relator (a skill que declara um
parecer final, ver team_context.is_relator), que então substitui este.

O relator da plataforma é uma skill oficial sem dono, como as skills originais:
ninguém edita nem desliga. Ela é criada na primeira vez que for necessária.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent_catalog.registry import register_skill
from app.agent_manifest.manifest import AgentSkillManifest
from app.models import AgentSkill, User

PLATFORM_RELATOR_NAME = "Relator da Plataforma"

PLATFORM_RELATOR = AgentSkillManifest(
    name=PLATFORM_RELATOR_NAME,
    version="1.0",
    author_origin="Flav.IA (componente da plataforma)",
    domain="Relatoria",
    objective=(
        "Consolidar os pareceres dos agentes de um comitê num parecer final único, com "
        "convergências, divergências resolvidas, riscos e conclusão."
    ),
    capabilities=[
        "Consolidar os pareceres de agentes de qualquer área",
        "Resolver divergências entre agentes com justificativa",
        "Apontar o que falta para uma decisão",
    ],
    expected_inputs=["Pareceres dos outros agentes da orquestração", "Solicitação e documentos anexados"],
    produced_outputs=["Parecer final do comitê", "Convergências e divergências", "Pendências para a decisão"],
    operating_limits=[
        "Não acrescenta fatos que não estejam nos pareceres, na solicitação ou nos anexos",
        "Recomenda; quem decide é uma pessoa",
    ],
    input_contract_ref="solicitacao_analise_schema.v1",
    output_contract_ref="resposta_especialista_schema.v1",
    security_rules=["Dados pessoais só pelas iniciais"],
    validation_criteria=["Considera o parecer de cada agente", "Diz de qual agente vem cada ponto"],
    persona_instructions=(
        "Você é o relator do comitê, um papel da plataforma, e não um especialista de uma área. "
        "Use a linguagem da área da solicitação, seja ela software, direito, saúde, finanças ou "
        "outra. Escreva o parecer final: os pontos em que os agentes concordam, as divergências "
        "e como você as resolve, os riscos principais, o que ainda falta para decidir e a "
        "conclusão. Considere todos os agentes e diga de qual deles vem cada ponto."
    ),
)


def platform_relator(db: Session, *, user: User) -> AgentSkill:
    """Devolve o relator da plataforma, criando-o na primeira vez."""
    existing = db.scalar(
        select(AgentSkill).where(
            AgentSkill.name == PLATFORM_RELATOR_NAME,
            AgentSkill.owner_id.is_(None),
            AgentSkill.visibility == "OFFICIAL",
        )
    )
    if existing is not None:
        return existing
    skill = register_skill(db, manifest=PLATFORM_RELATOR, submitted_by=user, owner_id=None)
    db.commit()
    return skill
