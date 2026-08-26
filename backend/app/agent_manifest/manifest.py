import re
import unicodedata
from typing import Literal

from pydantic import BaseModel, Field

DomainLiteral = Literal["codigo_legado", "regras_negocio", "arquitetura_software"]

# The RFC's two MCP-inspired schemas (Apêndice C) use two different domain
# enumerations (escopo_analise.analises_requeridas vs. agente_emissor.dominio).
# This project standardizes on the resposta_especialista_schema.json enum
# everywhere a domain is stored, to avoid carrying that inconsistency into code.
_DOMAIN_ALIASES: dict[str, DomainLiteral] = {
    "codigo legado": "codigo_legado",
    "codigo_legado": "codigo_legado",
    "legado": "codigo_legado",
    "regras de negocio": "regras_negocio",
    "regras_negocio": "regras_negocio",
    "negocio": "regras_negocio",
    "arquitetura de software": "arquitetura_software",
    "arquitetura_software": "arquitetura_software",
    "arquitetura": "arquitetura_software",
}

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

_SECTION_HEADER = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
_TITLE_HEADER = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
_IDENTIFICATION_FIELD = re.compile(r"^-\s*([^:]+):\s*(.*)$")
_BULLET_ITEM = re.compile(r"^-\s+(.+?)\s*$")


class ManifestParseError(ValueError):
    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


class AgentSkillManifest(BaseModel):
    name: str = Field(max_length=160)
    version: str = Field(max_length=30)
    author_origin: str
    domain: DomainLiteral
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


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    without_accents = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return without_accents.strip().lower()


def _resolve_domain(raw_value: str) -> DomainLiteral | None:
    return _DOMAIN_ALIASES.get(_normalize(raw_value))


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
            fields[_normalize(match.group(1))] = match.group(2).strip()
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

    domain: DomainLiteral | None = None
    if not raw_domain:
        errors.append("Campo 'Domínio de atuação' ausente na seção Identificação.")
    else:
        domain = _resolve_domain(raw_domain)
        if domain is None:
            errors.append(
                f"Domínio de atuação '{raw_domain}' não reconhecido. "
                "Use um de: código legado, regras de negócio, arquitetura de software."
            )

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
