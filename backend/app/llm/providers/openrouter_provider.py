import json

from app.core.config import Settings
from app.llm.base import LLMProvider
from app.llm.prompts import TECHNICAL_PLANNER_INSTRUCTIONS, build_technical_planner_prompt
from app.llm.schemas import LLMPlan, LLMPlanRequest, LLMProviderResult, LLMUsage


class OpenRouterLLMProvider(LLMProvider):
    """Model Gateway adapter for OpenRouter.

    Uses the Chat Completions surface (not the OpenAI Responses API): OpenRouter's
    documented compatibility and structured-output support target /chat/completions,
    and not every routed model implements the Responses API the same way OpenAI does.
    """

    name = "openrouter"

    def __init__(self, config: Settings) -> None:
        # Import is intentionally lazy: the project remains runnable with LLM disabled.
        from openai import OpenAI

        api_key = config.openrouter_api_key_value
        if not api_key:
            raise RuntimeError("A credencial da OpenRouter não foi configurada.")

        self.config = config
        self.client = OpenAI(
            api_key=api_key,
            base_url=config.openrouter_base_url,
            timeout=config.llm_timeout_seconds,
        )

    def generate_plan(
        self,
        request: LLMPlanRequest,
        *,
        llm_call_id: str,
    ) -> LLMProviderResult:
        schema = LLMPlan.model_json_schema()
        prompt = build_technical_planner_prompt(request)

        response = self.client.chat.completions.create(
            model=self.config.llm_model,
            messages=[
                {"role": "system", "content": TECHNICAL_PLANNER_INSTRUCTIONS},
                {"role": "user", "content": prompt},
            ],
            max_tokens=self.config.llm_max_output_tokens,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "technical_orchestration_plan",
                    "strict": True,
                    "schema": schema,
                },
            },
            extra_headers={
                "HTTP-Referer": self.config.openrouter_app_url,
                "X-Title": self.config.app_name,
                "X-Client-Request-Id": llm_call_id,
            },
        )

        message = response.choices[0].message.content
        if not message:
            raise RuntimeError("O provedor OpenRouter retornou uma resposta vazia.")
        plan = LLMPlan.model_validate(json.loads(message))
        usage = getattr(response, "usage", None)
        return LLMProviderResult(
            plan=plan,
            provider_response_id=getattr(response, "id", None),
            provider_request_id=getattr(response, "_request_id", None),
            usage=LLMUsage(
                input_tokens=getattr(usage, "prompt_tokens", None),
                output_tokens=getattr(usage, "completion_tokens", None),
            ),
        )
