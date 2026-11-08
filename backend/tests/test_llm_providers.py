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


# --- Uma chamada lenta não pode virar duas cobranças --------------------------
# 07/11/2026: com timeout de 45 s, o cliente da OpenAI desistia das respostas do
# gpt-5-mini (45 a 90 s) e repetia a chamada sozinho (max_retries=2 por padrão),
# enquanto a primeira continuava rodando e era cobrada na OpenRouter.

import httpx  # noqa: E402
import pytest  # noqa: E402
from openai import APIConnectionError, APITimeoutError  # noqa: E402

_REQUEST = httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")


def _provider_with(monkeypatch, create) -> tuple[OpenRouterLLMProvider, list[dict]]:
    init_kwargs: list[dict] = []

    class _Completions:
        def create(self, **kwargs):
            return create()

    class _Client:
        def __init__(self, **kwargs) -> None:
            init_kwargs.append(kwargs)
            self.chat = type("Chat", (), {"completions": _Completions()})()

    monkeypatch.setattr("openai.OpenAI", _Client)
    monkeypatch.setattr("app.core.retry.time.sleep", lambda _seconds: None)
    return OpenRouterLLMProvider(_build_settings()), init_kwargs


def test_cliente_nao_repete_chamadas_por_conta_propria(monkeypatch) -> None:
    _, init_kwargs = _provider_with(monkeypatch, lambda: None)

    assert init_kwargs[0]["max_retries"] == 0


def test_timeout_padrao_cobre_modelos_que_raciocinam() -> None:
    assert Settings().llm_timeout_seconds >= 180


def test_chamada_que_estoura_o_tempo_nao_e_repetida(monkeypatch) -> None:
    calls: list[int] = []

    def slow():
        calls.append(1)
        raise APITimeoutError(request=_REQUEST)

    provider, _ = _provider_with(monkeypatch, slow)

    with pytest.raises(APITimeoutError):
        provider.generate_plan(_build_request(), llm_call_id="c", model="openai/gpt-5-mini")
    assert len(calls) == 1


def test_falha_de_conexao_ainda_tenta_de_novo(monkeypatch) -> None:
    calls: list[int] = []

    def offline():
        calls.append(1)
        raise APIConnectionError(request=_REQUEST)

    provider, _ = _provider_with(monkeypatch, offline)

    with pytest.raises(APIConnectionError):
        provider.generate_plan(_build_request(), llm_call_id="c", model="openai/gpt-5-mini")
    assert len(calls) == 2


def test_embeddings_e_openai_tambem_sem_repeticao_escondida(monkeypatch) -> None:
    from app.llm.providers.openai_provider import OpenAILLMProvider
    from app.rag.providers.openrouter_embedding_provider import OpenRouterEmbeddingProvider

    captured: list[dict] = []
    monkeypatch.setattr("openai.OpenAI", lambda **kwargs: captured.append(kwargs) or object())

    OpenRouterEmbeddingProvider(_build_settings())
    openai_settings = _build_settings(llm_provider="openai", openai_api_key="sk-fake-openai-key-000000000000")
    OpenAILLMProvider(openai_settings)

    assert [kwargs["max_retries"] for kwargs in captured] == [0, 0]
