from abc import ABC, abstractmethod

from app.llm.schemas import LLMPlanRequest, LLMProviderResult


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
