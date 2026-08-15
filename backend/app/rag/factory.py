from sqlalchemy.orm import Session

from app.core.config import Settings, settings
from app.rag.base import EmbeddingProvider, Retriever
from app.rag.providers.mock_embedding_provider import MockEmbeddingProvider
from app.rag.providers.openrouter_embedding_provider import OpenRouterEmbeddingProvider
from app.rag.retriever import InMemoryVectorRetriever


def create_embedding_provider(config: Settings = settings) -> EmbeddingProvider:
    # Retrieval stays fully offline unless the model gateway is OpenRouter with a
    # real credential: the app must keep working with LLM/RAG disabled.
    if config.llm_provider == "openrouter" and config.openrouter_api_key_value:
        return OpenRouterEmbeddingProvider(config)

    return MockEmbeddingProvider()


def create_retriever(db: Session, config: Settings = settings) -> Retriever:
    embedding_provider = create_embedding_provider(config)
    return InMemoryVectorRetriever(db, embedding_provider)


__all__ = ["create_embedding_provider", "create_retriever"]
