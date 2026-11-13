from abc import ABC, abstractmethod

from app.llm.schemas import LLMPlanRequest, LLMProviderResult


class LLMEmptyResponseError(RuntimeError):
    """O provedor não devolveu conteúdo porque gastou LLM_MAX_OUTPUT_TOKENS em raciocínio
    oculto (finish_reason "length"). Não é passageiro: repetir com o mesmo limite falha
    do mesmo jeito.
    """


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
        """Gera um plano estruturado, sem executar ferramentas. O `model` é sempre resolvido
        por quem chama; o provedor nunca escolhe um modelo por conta própria.
        """
