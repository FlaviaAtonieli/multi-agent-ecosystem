from abc import ABC, abstractmethod

from app.llm.schemas import LLMPlanRequest, LLMProviderResult


class LLMEmptyResponseError(RuntimeError):
    """Raised when the provider returns no content because it exhausted
    LLM_MAX_OUTPUT_TOKENS on hidden reasoning tokens before writing any visible
    output (finish_reason="length"). A RuntimeError subclass on purpose: the
    providers' retry wrapper catches RuntimeError, so this gets retried like
    any other transient failure -- how many reasoning tokens a model burns
    for the same prompt isn't perfectly deterministic, so a second attempt
    isn't guaranteed to hit the same wall (see security review, PR #35, on
    app/llm/providers/openrouter_provider.py)."""


class LLMProvider(ABC):
    name: str

    @abstractmethod
    def generate_plan(
        self,
        request: LLMPlanRequest,
        *,
        llm_call_id: str,
        model: str,
    ) -> LLMProviderResult:
        """Generate a structured plan without executing tools or publishing artifacts.

        `model` is always resolved by the caller (llm_service.generate_technical_plan)
        before this is called -- the provider never falls back to its own config.
        """
