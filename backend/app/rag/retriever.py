import math

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import KnowledgeChunk
from app.rag.base import EmbeddingProvider, Retriever
from app.rag.schemas import RetrievedChunk


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class InMemoryVectorRetriever(Retriever):
    """Loads indexed chunks from the relational database and ranks them in memory.

    Deliberately avoids pgvector/ANN indexes: the PoC fixture holds a small number
    of chunks (tens to a few hundred), so a linear scan with cosine similarity in
    pure Python is fast enough and keeps the same schema portable across SQLite
    (dev/tests) and PostgreSQL (production), where a Vector column would not be.
    """

    def __init__(self, db: Session, embedding_provider: EmbeddingProvider) -> None:
        self.db = db
        self.embedding_provider = embedding_provider

    def retrieve(self, query: str, *, top_k: int) -> list[RetrievedChunk]:
        chunks = list(self.db.scalars(select(KnowledgeChunk)))
        if not chunks:
            return []

        query_embedding = self.embedding_provider.embed([query])[0]
        scored = [
            (
                _cosine_similarity(query_embedding, chunk.embedding or []),
                chunk,
            )
            for chunk in chunks
        ]
        scored.sort(key=lambda pair: pair[0], reverse=True)

        return [
            RetrievedChunk(
                chunk_id=chunk.id,
                artifact_name=chunk.artifact_name,
                content=chunk.content,
                score=score,
                metadata={
                    "source_type": chunk.source_type,
                    "language": chunk.language,
                    "chunk_index": chunk.chunk_index,
                },
            )
            for score, chunk in scored[:top_k]
            if score > 0
        ]
