import json

from app.core.config import Settings
from app.llm.providers.openrouter_provider import OpenRouterLLMProvider
from app.llm.schemas import LLMPlanRequest
from app.llm.security import sanitize_content


class _FakeMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class _FakeChoice:
    def __init__(self, content: str) -> None:
        self.message = _FakeMessage(content)


class _FakeUsage:
    def __init__(self, prompt_tokens: int, completion_tokens: int) -> None:
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens


class _FakeChatCompletionResponse:
    def __init__(self, content: str) -> None:
        self.id = "gen-fake-id"
        self.choices = [_FakeChoice(content)]
        self.usage = _FakeUsage(prompt_tokens=10, completion_tokens=20)


class _FakeCompletions:
    def __init__(self, captured_calls: list[dict]) -> None:
        self._captured_calls = captured_calls

    def create(self, **kwargs):
        self._captured_calls.append(kwargs)
        plan = {
            "summary": "Plano gerado via OpenRouter para validação de contrato.",
            "required_agents": ["technical_planner"],
            "required_skills": ["analyze_request_context"],
            "risks": [],
            "missing_information": [],
            "requires_human_approval": True,
        }
        return _FakeChatCompletionResponse(json.dumps(plan))


class _FakeChat:
    def __init__(self, captured_calls: list[dict]) -> None:
        self.completions = _FakeCompletions(captured_calls)


class _FakeOpenAIClient:
    def __init__(self, captured_calls: list[dict]) -> None:
        self.chat = _FakeChat(captured_calls)


def _build_settings(**overrides) -> Settings:
    base = {
        "llm_enabled": True,
        "llm_provider": "openrouter",
        "llm_model": "openai/gpt-5-mini",
        "llm_allowed_models": "openai/gpt-5-mini",
        "openrouter_api_key": "sk-or-v1-fake-key-for-tests-0000000000000000",
    }
    base.update(overrides)
    return Settings(**base)


def _build_request() -> LLMPlanRequest:
    return LLMPlanRequest(
        technical_request_id="req-1",
        trace_id="TRC-20260811-AAAAAA",
        title="Analisar impacto de mudança",
        problem="Problema de teste para validar o adapter OpenRouter.",
        objective="Gerar plano técnico sem executar ferramentas.",
        context="Contexto suficiente para qualificar a solicitação de teste.",
        restrictions=["Não executar tools"],
    )


def test_openrouter_provider_parses_chat_completions_response(monkeypatch) -> None:
    captured_calls: list[dict] = []
    captured_init_kwargs: list[dict] = []

    def fake_openai_factory(**kwargs):
        captured_init_kwargs.append(kwargs)
        return _FakeOpenAIClient(captured_calls)

    monkeypatch.setattr("openai.OpenAI", fake_openai_factory)

    provider = OpenRouterLLMProvider(_build_settings())
    result = provider.generate_plan(_build_request(), llm_call_id="call-123", model="openai/gpt-5-mini")

    assert result.plan.summary.startswith("Plano gerado via OpenRouter")
    assert result.usage.input_tokens == 10
    assert result.usage.output_tokens == 20
    assert result.provider_response_id == "gen-fake-id"

    assert captured_init_kwargs[0]["base_url"] == "https://openrouter.ai/api/v1"

    call_kwargs = captured_calls[0]
    assert call_kwargs["model"] == "openai/gpt-5-mini"
    assert call_kwargs["extra_headers"]["X-Client-Request-Id"] == "call-123"
    assert call_kwargs["response_format"]["json_schema"]["strict"] is True


def test_openrouter_provider_requires_credential() -> None:
    config = _build_settings(openrouter_api_key=None, llm_enabled=False)
    try:
        OpenRouterLLMProvider(config)
        raise AssertionError("Deveria levantar RuntimeError sem credencial.")
    except RuntimeError as exc:
        assert "OpenRouter" in str(exc)


def test_openrouter_style_key_is_redacted_by_security_sanitizer() -> None:
    content = "Minha chave é sk-or-v1-abcdefghijklmnopqrstuvwxyz0123456789ABCDEF"
    sanitized = sanitize_content(content, max_chars=1000, redact=True)
    assert "[REDACTED_API_KEY]" in sanitized.value
    assert "sk-or-v1" not in sanitized.value
    assert sanitized.redacted_fields_count == 1
