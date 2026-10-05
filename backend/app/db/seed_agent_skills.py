from sqlalchemy import select

from app.agent_catalog.registry import register_skill
from app.agent_manifest.manifest import AgentSkillManifest
from app.core.database import SessionLocal
from app.core.roles import ROLE_ADMIN
from app.models import AgentSkill, User

# Cada entrada aqui é um domínio que ainda não tem uma Agent Skill OFFICIAL no
# catálogo (checado por domínio, não por nome -- um domínio só ganha uma
# oficial por vez). Os 4 domínios originais (codigo_legado, regras_negocio,
# arquitetura_software, seguranca_informacao) não entram nesta lista porque já
# foram cadastrados manualmente, uma vez, pela tela -- esta seed só existe para
# não repetir esse passo manual a cada domínio novo adicionado ao catálogo.
_NEW_OFFICIAL_SKILLS: list[AgentSkillManifest] = [
    AgentSkillManifest(
        name="Agent Skill de Qualidade e Testes",
        version="1.0",
        author_origin="Equipe AgentHub (PoC acadêmica)",
        domain="qualidade_testes",
        objective=(
            "Avaliar a cobertura de testes automatizados e o risco de regressão de uma "
            "mudança solicitada, usando evidência recuperada da base de conhecimento "
            "indexada (auditorias de cobertura, suítes de teste existentes)."
        ),
        capabilities=[
            "Recuperar evidência de cobertura de teste e testes existentes",
            "Identificar lacunas de cobertura em componentes críticos",
            "Sinalizar testes instáveis (flaky) e risco de regressão sem rede de segurança",
        ],
        expected_inputs=["Problema técnico", "Objetivo", "Contexto da solicitação"],
        produced_outputs=["Resumo executivo", "Lacunas de cobertura identificadas", "Nível de confiança"],
        operating_limits=["Não escreve nem executa testes automaticamente"],
        input_contract_ref="solicitacao_analise_schema.v1",
        output_contract_ref="resposta_especialista_schema.v1",
        validation_criteria=["Contrato de saída válido"],
        persona_instructions=(
            "Você é um especialista em qualidade de software e estratégia de testes "
            "automatizados. Analise a solicitação focando em: cobertura de teste "
            "existente nos componentes envolvidos, lacunas em cenários críticos, "
            "testes instáveis (flaky) e risco de regressão quando não há teste "
            "automatizado cobrindo a mudança. Baseie-se nas evidências recuperadas "
            "da base de conhecimento."
        ),
    ),
]


def seed_agent_skills() -> None:
    """Garante uma Agent Skill OFFICIAL por domínio em _NEW_OFFICIAL_SKILLS,
    sem duplicar se já existir (idempotente, mesmo espírito de
    seed_knowledge_base.py). Precisa de pelo menos um usuário ADMIN já
    existente (ver bootstrap_admin em app/db/init_db.py) para atribuir como
    submitted_by/owner -- sem ADMIN, pula com um aviso."""
    with SessionLocal() as db:
        admin = db.scalar(select(User).where(User.role == ROLE_ADMIN).order_by(User.created_at))
        if admin is None:
            print("Nenhum usuário ADMIN encontrado -- rode bootstrap_admin antes desta seed.")
            return

        for manifest in _NEW_OFFICIAL_SKILLS:
            existing = db.scalar(
                select(AgentSkill).where(
                    AgentSkill.domain == manifest.domain, AgentSkill.visibility == "OFFICIAL"
                )
            )
            if existing:
                print(
                    f"{manifest.domain}: já existe uma Agent Skill OFFICIAL "
                    f"('{existing.name}'). Nada a fazer."
                )
                continue

            skill = register_skill(
                db,
                manifest=manifest,
                submitted_by=admin,
                owner_id=admin.id,
                visibility="OFFICIAL",
            )
            print(f"{manifest.domain}: Agent Skill '{skill.name}' registrada.")

        db.commit()


if __name__ == "__main__":
    seed_agent_skills()
