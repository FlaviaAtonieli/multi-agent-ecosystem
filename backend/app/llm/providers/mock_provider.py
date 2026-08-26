from app.llm.base import LLMProvider
from app.llm.schemas import LLMPlan, LLMPlanRequest, LLMProviderResult, LLMUsage


class MockLLMProvider(LLMProvider):
    name = "mock"

    def __init__(self, *, model: str = "mock-technical-planner-v1") -> None:
        self.model = model

    def generate_plan(
        self,
        request: LLMPlanRequest,
        *,
        llm_call_id: str,
    ) -> LLMProviderResult:
        missing_information: list[str] = []
        if not request.context:
            missing_information.append("Contexto técnico detalhado")
        if not request.restrictions:
            missing_information.append("Restrições de execução e publicação")

        return LLMProviderResult(
            plan=LLMPlan(
                summary=(
                    "Plano simulado para validar a arquitetura de integração. "
                    "Nenhuma chamada externa, tool ou publicação foi executada."
                ),
                required_agents=[
                    "requirements_analyst",
                    "technical_planner",
                    "quality_gate",
                ],
                required_skills=[
                    "analyze_request_context",
                    "build_execution_plan",
                ],
                risks=[
                    "Resultado gerado pelo provedor mock e não por uma LLM externa.",
                    "A execução real deve permanecer sujeita à aprovação humana.",
                ],
                missing_information=missing_information,
                requires_human_approval=True,
            ),
            provider_response_id=f"mock-{llm_call_id}",
            usage=LLMUsage(input_tokens=None, output_tokens=None),
        )
