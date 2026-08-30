from abc import ABC, abstractmethod

from app.llm.schemas import LLMPlanRequest, LLMProviderResult


class LLMEmptyResponseError(RuntimeError):
    """Raised when the provider returns no content because it exhausted
    LLM_MAX_OUTPUT_TOKENS on hidden reasoning tokens before writing any visible
    output (finish_reason="length") -- distinct from a transient empty response,
    since retrying the identical request/budget fails the same way every time."""


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
