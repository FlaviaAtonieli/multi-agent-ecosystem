"""Um executor e um servidor MCP para todas as Agent Skills.

Os cinco executores eram 86% a 90% iguais: mudavam só as frases sobre a
evidência. Estes testes fixam essas frases, para a unificação não mudar o que a
pessoa lê, e garantem que toda skill passa pelo mesmo servidor MCP.
"""

import pytest

from app.agent_catalog.mcp_client import SKILL_SERVER_MODULE, _module_for_skill
from app.agent_catalog.tool_interface import evidence_wording
from app.models import AgentSkill


@pytest.mark.parametrize(
    ("domain", "finding", "found", "nothing"),
    [
        (
            "codigo_legado",
            "Trecho recuperado da base de conhecimento como evidência relevante para a análise solicitada.",
            "3 trecho(s) de evidência recuperados",
            "Nenhum trecho relevante foi recuperado da base de conhecimento; a análise carece de "
            "evidência documental direta.",
        ),
        (
            "regras_negocio",
            "Trecho recuperado da base de conhecimento como evidência de regra de negócio "
            "potencialmente impactada pela mudança solicitada.",
            "3 trecho(s) de regra de negócio recuperados",
            "Nenhum trecho relevante foi recuperado da base de conhecimento; a análise de regras de "
            "negócio carece de evidência documental direta.",
        ),
        (
            "arquitetura_software",
            "Trecho recuperado da base de conhecimento como evidência de impacto arquitetural "
            "(acoplamento, limites de módulo ou risco estrutural).",
            "3 trecho(s) de evidência arquitetural recuperados",
            "Nenhum trecho relevante foi recuperado da base de conhecimento; a análise arquitetural "
            "carece de evidência documental direta.",
        ),
        (
            "seguranca_informacao",
            "Trecho recuperado da base de conhecimento como evidência de risco de segurança "
            "(exposição de dados, controle de acesso ou superfície de injeção).",
            "3 trecho(s) de evidência de segurança recuperados",
            "Nenhum trecho relevante foi recuperado da base de conhecimento; a análise de segurança "
            "carece de evidência documental direta.",
        ),
    ],
)
def test_areas_oficiais_mantem_as_frases(domain: str, finding: str, found: str, nothing: str) -> None:
    wording = evidence_wording(domain)

    assert wording.finding == finding
    assert wording.found(3).startswith(found)
    assert wording.nothing == nothing


def test_area_livre_usa_as_frases_gerais() -> None:
    assert evidence_wording("game_design") == evidence_wording("codigo_legado")


def test_frases_de_confianca_media_citam_as_lacunas() -> None:
    assert evidence_wording("regras_negocio").partial(2, 4) == (
        "2 trecho(s) de regra de negócio recuperados, mas o planejador técnico identificou "
        "4 lacuna(s) de informação."
    )
    assert evidence_wording("codigo_legado").found(2) == (
        "2 trecho(s) de evidência recuperados e nenhuma lacuna de informação identificada pelo "
        "planejador técnico."
    )


@pytest.mark.parametrize("owner_id", [None, "dono-1"])
@pytest.mark.parametrize(
    "domain", ["codigo_legado", "seguranca_informacao", "apis_integracoes", "game_design"]
)
def test_toda_skill_roda_no_mesmo_servidor_mcp(domain: str, owner_id: str | None) -> None:
    skill = AgentSkill(domain=domain, owner_id=owner_id)

    assert _module_for_skill(skill) == SKILL_SERVER_MODULE
