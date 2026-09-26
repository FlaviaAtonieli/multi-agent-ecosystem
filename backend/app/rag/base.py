from abc import ABC, abstractmethod

from app.rag.schemas import RetrievedChunk


class EmbeddingProvider(ABC):
    """Turns text into a fixed-size vector used for similarity search."""

    name: str

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Returns one embedding vector per input text, in the same order."""


class Retriever(ABC):
    """Finds the knowledge chunks most relevant to a query."""

    @abstractmethod
    def retrieve(self, query: str, *, top_k: int) -> list[RetrievedChunk]:
        """Returns up to top_k chunks ranked by relevance to the query."""
