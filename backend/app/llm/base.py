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
    ) -> LLMProviderResult:
        """Generate a structured plan without executing tools or publishing artifacts."""
