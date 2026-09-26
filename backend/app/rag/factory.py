from sqlalchemy.orm import Session

from app.core.config import Settings, settings
from app.rag.base import EmbeddingProvider, Retriever
from app.rag.providers.openrouter_embedding_provider import OpenRouterEmbeddingProvider
from app.rag.retriever import InMemoryVectorRetriever


class RAGConfigurationError(RuntimeError):
    pass


def create_embedding_provider(config: Settings = settings) -> EmbeddingProvider:
    if config.llm_provider != "openrouter" or not config.openrouter_api_key_value:
        raise RAGConfigurationError(
            "A recuperação de conhecimento (RAG) exige um Model Gateway OpenRouter "
            "configurado com credencial válida."
        )

    return OpenRouterEmbeddingProvider(config)


def create_retriever(db: Session, config: Settings = settings) -> Retriever:
    embedding_provider = create_embedding_provider(config)
    return InMemoryVectorRetriever(db, embedding_provider)


__all__ = ["create_embedding_provider", "create_retriever"]
