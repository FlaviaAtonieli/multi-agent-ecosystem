import json

from app.core.config import Settings
from app.llm.base import LLMProvider
from app.llm.prompts import TECHNICAL_PLANNER_INSTRUCTIONS, build_technical_planner_prompt
from app.llm.schemas import LLMPlan, LLMPlanRequest, LLMProviderResult, LLMUsage


class OpenAILLMProvider(LLMProvider):
    name = "openai"

    def __init__(self, config: Settings) -> None:
        # Import is intentionally lazy: the project remains runnable with LLM disabled.
        from openai import OpenAI

        api_key = config.openai_api_key_value
        if not api_key:
            raise RuntimeError("A credencial da OpenAI não foi configurada.")

        self.config = config
        self.client = OpenAI(
            api_key=api_key,
            base_url=config.openai_base_url,
            timeout=config.llm_timeout_seconds,
        )

    def generate_plan(
        self,
        request: LLMPlanRequest,
        *,
        llm_call_id: str,
        model: str,
    ) -> LLMProviderResult:
        schema = LLMPlan.model_json_schema()
        prompt = build_technical_planner_prompt(request)

        response = self.client.responses.create(
            model=model,
            instructions=TECHNICAL_PLANNER_INSTRUCTIONS,
            input=prompt,
            max_output_tokens=self.config.llm_max_output_tokens,
            store=self.config.llm_store_provider_response,
            text={
                "format": {
                    "type": "json_schema",
                    "name": "technical_orchestration_plan",
                    "description": "Plano técnico rastreável sem execução automática.",
                    "strict": True,
                    "schema": schema,
                }
            },
            extra_headers={"X-Client-Request-Id": llm_call_id},
        )

        plan = LLMPlan.model_validate(json.loads(response.output_text))
        usage = getattr(response, "usage", None)
        return LLMProviderResult(
            plan=plan,
            provider_response_id=getattr(response, "id", None),
            provider_request_id=getattr(response, "_request_id", None),
            usage=LLMUsage(
                input_tokens=getattr(usage, "input_tokens", None),
                output_tokens=getattr(usage, "output_tokens", None),
            ),
        )
