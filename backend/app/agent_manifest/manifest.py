import re
import unicodedata
from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field, StringConstraints


def normalize_domain_key(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    without_accents = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return " ".join(without_accents.lower().split())


# The domain is the area a skill declares: free text, since a skill can belong to
# any area (contabilidade, jurídico...), not only to the catalog below. These are
# the 10 domains of the official catalog, with the spellings a manifest can use for
# them, so they keep a single stored value. The Orquestrador itself
# (agent_skill_orchestration_service.py, orchestration_service.py,
# quality_gate/service.py) operates generically over "whichever skills matched the
# requested domain," regardless of how many domains exist.
_DOMAIN_ALIASES: dict[str, str] = {
    "codigo legado": "codigo_legado",
    "codigo_legado": "codigo_legado",
    "legado": "codigo_legado",
    "regras de negocio": "regras_negocio",
    "regras_negocio": "regras_negocio",
    "negocio": "regras_negocio",
    "arquitetura de software": "arquitetura_software",
    "arquitetura_software": "arquitetura_software",
    "arquitetura": "arquitetura_software",
    "seguranca da informacao": "seguranca_informacao",
    "seguranca_informacao": "seguranca_informacao",
    "seguranca": "seguranca_informacao",
    "qualidade e testes": "qualidade_testes",
    "qualidade_testes": "qualidade_testes",
    "testes": "qualidade_testes",
    "qualidade": "qualidade_testes",
    "observabilidade e monitoramento": "observabilidade_monitoramento",
    "observabilidade_monitoramento": "observabilidade_monitoramento",
    "observabilidade": "observabilidade_monitoramento",
    "monitoramento": "observabilidade_monitoramento",
    "performance e escalabilidade": "performance_escalabilidade",
    "performance_escalabilidade": "performance_escalabilidade",
    "performance": "performance_escalabilidade",
    "escalabilidade": "performance_escalabilidade",
    "dados e privacidade": "dados_privacidade",
    "dados_privacidade": "dados_privacidade",
    "privacidade": "dados_privacidade",
    "lgpd": "dados_privacidade",
    "infraestrutura e devops": "infraestrutura_devops",
    "infraestrutura_devops": "infraestrutura_devops",
    "infraestrutura": "infraestrutura_devops",
    "devops": "infraestrutura_devops",
    "apis e integracoes": "apis_integracoes",
    "apis_integracoes": "apis_integracoes",
    "apis": "apis_integracoes",
    "integracoes": "apis_integracoes",
}

# RFC §6.1 "Proteção de Contexto": human-readable label used to scope both the
# RAG retrieval query and the LLM prompt to a single skill's domain, instead of
# every skill seeing the exact same unscoped context.
DOMAIN_LABELS: dict[str, str] = {
    "codigo_legado": "Código Legado",
    "regras_negocio": "Regras de Negócio",
    "arquitetura_software": "Arquitetura de Software",
    "seguranca_informacao": "Segurança da Informação",
    "qualidade_testes": "Qualidade e Testes",
    "observabilidade_monitoramento": "Observabilidade e Monitoramento",
    "performance_escalabilidade": "Performance e Escalabilidade",
    "dados_privacidade": "Dados e Privacidade (LGPD)",
    "infraestrutura_devops": "Infraestrutura e DevOps",
    "apis_integracoes": "APIs e Integrações",
}
_DOMAIN_ALIASES.update({normalize_domain_key(label): domain for domain, label in DOMAIN_LABELS.items()})

MAX_DOMAIN_LENGTH = 60


def resolve_domain(raw_value: str) -> str:
    """Maps a known spelling to its catalog domain. Any other area is kept as
    typed, only with the whitespace cleaned up."""
    return _DOMAIN_ALIASES.get(normalize_domain_key(raw_value), " ".join(raw_value.split()))


DomainName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=2, max_length=MAX_DOMAIN_LENGTH),
    AfterValidator(resolve_domain),
]

_REQUIRED_SECTIONS = (
    "Identificação",
    "Objetivo",
    "Capacidades",
    "Entradas Esperadas",
    "Saídas Produzidas",
    "Limites de Atuação",
    "Contrato de Entrada",
    "Contrato de Saída",
    "Regras de Segurança",
    "Exemplos de Uso",
    "Critérios de Validação",
)

# O manifesto vem de upload: cada parte destas expressões aceita caracteres que a
# seguinte não aceita, para o tempo não crescer de forma quadrática com um texto
# cheio de espaços. Os espaços nas pontas saem com strip() em quem usa o resultado.
_SECTION_HEADER = re.compile(r"^##[ \t]+(\S.*)$", re.MULTILINE)
_TITLE_HEADER = re.compile(r"^#[ \t]+(\S.*)$", re.MULTILINE)
_IDENTIFICATION_FIELD = re.compile(r"^-\s*([^:\s][^:]*):(.*)$")
_BULLET_ITEM = re.compile(r"^-\s+(\S.*)$")


class ManifestParseError(ValueError):
    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


class AgentSkillManifest(BaseModel):
    name: str = Field(max_length=160)
    version: str = Field(max_length=30)
    author_origin: str
    domain: DomainName
    objective: str
    capabilities: list[str] = Field(default_factory=list)
    expected_inputs: list[str] = Field(default_factory=list)
    produced_outputs: list[str] = Field(default_factory=list)
    operating_limits: list[str] = Field(default_factory=list)
    input_contract_ref: str
    output_contract_ref: str
    security_rules: list[str] = Field(default_factory=list)
    usage_examples: list[str] = Field(default_factory=list)
    validation_criteria: list[str] = Field(default_factory=list)
    uses_external_services: bool = False
    # Instruções da skill, levadas ao prompt pelo SkillExecutor (tool_interface.py).
    persona_instructions: str | None = Field(default=None, max_length=4000)


def _split_sections(content: str) -> tuple[str | None, dict[str, str]]:
    title_match = _TITLE_HEADER.search(content)
    title = title_match.group(1).strip() if title_match else None

    headers = list(_SECTION_HEADER.finditer(content))
    sections: dict[str, str] = {}
    for index, match in enumerate(headers):
        section_name = match.group(1).strip()
        start = match.end()
        end = headers[index + 1].start() if index + 1 < len(headers) else len(content)
        sections[section_name] = content[start:end].strip()

    return title, sections


def _extract_bullets(block: str) -> list[str]:
    items = []
    for line in block.splitlines():
        match = _BULLET_ITEM.match(line.strip())
        if match:
            items.append(match.group(1).strip())
    if items:
        return items
    stripped = block.strip()
    return [stripped] if stripped else []


def _extract_identification_fields(block: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in block.splitlines():
        match = _IDENTIFICATION_FIELD.match(line.strip())
        if match:
            fields[normalize_domain_key(match.group(1))] = match.group(2).strip()
    return fields


def parse_modelo_md(content: str) -> AgentSkillManifest:
    """Parses a modelo.md manifest (Apêndice G da RFC) into an AgentSkillManifest.

    Raises ManifestParseError listing every missing/invalid section at once,
    so an invalid import (Cenário 2, Apêndice H da RFC) can show the user a
    full list of what needs fixing instead of failing on the first problem.
    """
    errors: list[str] = []

    title, sections = _split_sections(content)
    if not title:
        errors.append("Título do agente (heading `# Nome do Agente`) ausente.")

    for required in _REQUIRED_SECTIONS:
        if required not in sections or not sections[required].strip():
            errors.append(f"Seção obrigatória ausente ou vazia: '{required}'.")

    identification = _extract_identification_fields(sections.get("Identificação", ""))
    version = identification.get("versao") or identification.get("versão")
    author_origin = identification.get("autor/origem") or identification.get("autor")
    raw_domain = identification.get("dominio de atuacao") or identification.get("domínio de atuação")

    if not version:
        errors.append("Campo 'Versão' ausente na seção Identificação.")
    if not author_origin:
        errors.append("Campo 'Autor/Origem' ausente na seção Identificação.")

    domain: str | None = None
    if not raw_domain:
        errors.append("Campo 'Domínio de atuação' ausente na seção Identificação.")
    elif not 2 <= len(raw_domain) <= MAX_DOMAIN_LENGTH:
        errors.append(f"Domínio de atuação deve ter de 2 a {MAX_DOMAIN_LENGTH} caracteres.")
    else:
        domain = raw_domain

    if errors:
        raise ManifestParseError(errors)

    assert title is not None and version is not None and author_origin is not None and domain is not None

    return AgentSkillManifest(
        name=title,
        version=version,
        author_origin=author_origin,
        domain=domain,
        objective=sections["Objetivo"].strip(),
        capabilities=_extract_bullets(sections["Capacidades"]),
        expected_inputs=_extract_bullets(sections["Entradas Esperadas"]),
        produced_outputs=_extract_bullets(sections["Saídas Produzidas"]),
        operating_limits=_extract_bullets(sections["Limites de Atuação"]),
        input_contract_ref=sections["Contrato de Entrada"].strip(),
        output_contract_ref=sections["Contrato de Saída"].strip(),
        security_rules=_extract_bullets(sections["Regras de Segurança"]),
        usage_examples=_extract_bullets(sections["Exemplos de Uso"]),
        validation_criteria=_extract_bullets(sections["Critérios de Validação"]),
    )
