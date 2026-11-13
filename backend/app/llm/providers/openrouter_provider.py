import json

from pydantic import ValidationError

from app.core.config import Settings
from app.core.retry import retry_on_transient_error
from app.llm.base import LLMEmptyResponseError, LLMProvider
from app.llm.prompts import TECHNICAL_PLANNER_INSTRUCTIONS, build_technical_planner_prompt
from app.llm.schemas import LLMPlan, LLMPlanRequest, LLMProviderResult, LLMUsage, strict_json_schema


class OpenRouterLLMProvider(LLMProvider):
    """Adaptador do Model Gateway para a OpenRouter.

    Usa Chat Completions, e não a Responses API da OpenAI: é nela que a OpenRouter
    documenta compatibilidade e saída estruturada, e nem todo modelo roteado implementa
    a Responses API do mesmo jeito.
    """

    name = "openrouter"

    def __init__(self, config: Settings) -> None:
        # Import dentro da função: o projeto roda sem esta biblioteca com o LLM desligado.
        from openai import OpenAI

        api_key = config.openrouter_api_key_value
        if not api_key:
            raise RuntimeError("A credencial da OpenRouter não foi configurada.")

        self.config = config
        self.client = OpenAI(
            api_key=api_key,
            base_url=config.openrouter_base_url,
            timeout=config.llm_timeout_seconds,
            # Sem repetição escondida: quando o cliente desiste por tempo, a chamada
            # original continua rodando e é cobrada. Quem repete é retry_on_transient_error.
            max_retries=0,
        )

    def generate_plan(
        self,
        request: LLMPlanRequest,
        *,
        llm_call_id: str,
        model: str,
    ) -> LLMProviderResult:
        from openai import APIConnectionError, APITimeoutError, RateLimitError

        schema = strict_json_schema(LLMPlan)
        prompt = build_technical_planner_prompt(request)

        def _call() -> LLMProviderResult:
            extra_kwargs: dict = {}
            if self.config.llm_max_output_tokens:
                extra_kwargs["max_tokens"] = self.config.llm_max_output_tokens
            if self.config.llm_temperature is not None:
                extra_kwargs["temperature"] = self.config.llm_temperature
            if self.config.llm_seed is not None:
                extra_kwargs["seed"] = self.config.llm_seed

            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": TECHNICAL_PLANNER_INSTRUCTIONS},
                    {"role": "user", "content": prompt},
                ],
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
                **extra_kwargs,
            )

            choice = response.choices[0]
            message = choice.message.content
            if not message:
                if choice.finish_reason == "length":
                    # Modelos que raciocinam podem gastar todo o max_tokens antes da resposta visível.
                    # Não adianta repetir: o mesmo prompt com o mesmo limite falha igual.
                    raise LLMEmptyResponseError(
                        "O modelo esgotou o orçamento de tokens de saída "
                        "(LLM_MAX_OUTPUT_TOKENS) processando raciocínio interno, "
                        "antes de gerar conteúdo visível."
                    )
                raise RuntimeError("O provedor OpenRouter retornou uma resposta vazia.")
            # Um modelo gratuito às vezes ignora o json_schema e devolve JSON válido, mas
            # incompleto; é repetido abaixo como as outras falhas passageiras.
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

        return retry_on_transient_error(
            _call,
            exceptions=(
                RuntimeError,
                json.JSONDecodeError,
                ValidationError,
                RateLimitError,
                APIConnectionError,
            ),
            # APITimeoutError é subclasse de APIConnectionError, mas não se repete: o
            # provedor continua processando a chamada que estourou o tempo, e repetir
            # pagaria duas vezes.
            never_retry=(APITimeoutError,),
        )
