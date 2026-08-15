import re

from pydantic import BaseModel, Field

from app.agent_manifest.manifest import AgentSkillManifest

_SEMVER_PATTERN = re.compile(r"^\d+\.\d+(\.\d+)?$")


class ValidationResult(BaseModel):
    is_valid: bool
    errors: list[str] = Field(default_factory=list)


def validate_manifest(manifest: AgentSkillManifest) -> ValidationResult:
    """Checks governance rules from RF03/RFC §6.4: a skill is only registered
    when it declares name, domain, version, I/O contracts, operating limits,
    external-service usage, validation criteria and origin/owner."""
    errors: list[str] = []

    if not manifest.name.strip():
        errors.append("Nome do agente é obrigatório.")
    if not _SEMVER_PATTERN.match(manifest.version.strip()):
        errors.append(
            f"Versão '{manifest.version}' não segue o formato esperado (ex.: 1.0 ou 1.0.0)."
        )
    if not manifest.author_origin.strip():
        errors.append("Autor/origem do agente é obrigatório.")
    if not manifest.objective.strip():
        errors.append("Objetivo do agente é obrigatório.")
    if not manifest.capabilities:
        errors.append("A skill precisa declarar ao menos uma capacidade.")
    if not manifest.expected_inputs:
        errors.append("A skill precisa declarar ao menos uma entrada esperada.")
    if not manifest.produced_outputs:
        errors.append("A skill precisa declarar ao menos uma saída produzida.")
    if not manifest.operating_limits:
        errors.append(
            "A skill precisa declarar seus limites de atuação explicitamente "
            "(o que ela NÃO pode fazer)."
        )
    if not manifest.input_contract_ref.strip():
        errors.append("Contrato de entrada é obrigatório.")
    if not manifest.output_contract_ref.strip():
        errors.append("Contrato de saída é obrigatório.")
    if not manifest.validation_criteria:
        errors.append("A skill precisa declarar critérios mínimos de validação.")

    return ValidationResult(is_valid=not errors, errors=errors)
