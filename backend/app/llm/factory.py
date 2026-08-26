from app.core.config import Settings, settings
from app.llm.base import LLMProvider
from app.llm.providers.mock_provider import MockLLMProvider
from app.llm.providers.openai_provider import OpenAILLMProvider
from app.llm.providers.openrouter_provider import OpenRouterLLMProvider


class LLMConfigurationError(RuntimeError):
    pass


def create_llm_provider(config: Settings = settings) -> LLMProvider:
    if config.llm_provider == "mock":
        return MockLLMProvider(model=config.llm_model)

    if config.llm_provider == "openai":
        if not config.openai_api_key_value:
            raise LLMConfigurationError("A credencial do provedor OpenAI não foi configurada.")
        return OpenAILLMProvider(config)

    if config.llm_provider == "openrouter":
        if not config.openrouter_api_key_value:
            raise LLMConfigurationError("A credencial do provedor OpenRouter não foi configurada.")
        return OpenRouterLLMProvider(config)

    raise LLMConfigurationError("O provedor de LLM configurado não é suportado.")
