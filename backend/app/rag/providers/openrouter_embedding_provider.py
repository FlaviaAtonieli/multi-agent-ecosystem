from app.core.config import Settings
from app.rag.base import EmbeddingProvider


class OpenRouterEmbeddingProvider(EmbeddingProvider):
    """Embedding provider backed by an OpenAI-compatible embeddings endpoint via OpenRouter."""

    name = "openrouter"

    def __init__(self, config: Settings, *, model: str = "openai/text-embedding-3-small") -> None:
        # Import is intentionally lazy: the project remains runnable with LLM/RAG disabled.
        from openai import OpenAI

        api_key = config.openrouter_api_key_value
        if not api_key:
            raise RuntimeError("A credencial da OpenRouter não foi configurada.")

        self.model = model
        self.client = OpenAI(
            api_key=api_key,
            base_url=config.openrouter_base_url,
            timeout=config.llm_timeout_seconds,
        )

    def embed(self, texts: list[str]) -> list[list[float]]:
        response = self.client.embeddings.create(model=self.model, input=texts)
        return [item.embedding for item in response.data]
