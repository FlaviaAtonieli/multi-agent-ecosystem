from app.llm.prompts import build_technical_planner_prompt
from app.llm.schemas import LLMPlanRequest


def _base_request(**overrides) -> LLMPlanRequest:
    defaults = dict(
        technical_request_id="req-1",
        trace_id="TRC-20260826-AAAAAA",
        title="Analisar impacto de mudanca",
        problem="Problema de teste.",
        objective="Objetivo de teste.",
        context="Contexto de teste.",
        restrictions=["Nao executar tools"],
    )
    defaults.update(overrides)
    return LLMPlanRequest(**defaults)


def test_prompt_without_domain_has_no_scoping_instruction() -> None:
    prompt = build_technical_planner_prompt(_base_request())
    assert "Domínio de análise" not in prompt


def test_prompt_with_domain_scopes_the_analysis() -> None:
    """RFC §6.1 "Protecao de Contexto": a skill should be steered to analyze
    only its own domain, not asked to opine on the others."""
    prompt = build_technical_planner_prompt(
        _base_request(analysis_domain_label="Segurança da Informação")
    )
    assert "Domínio de análise: Segurança da Informação" in prompt
    assert "exclusivamente" in prompt
