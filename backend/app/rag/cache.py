"""Cache de embeddings no banco.

Os embeddings são determinísticos para o mesmo texto e modelo, então repetir a chamada
só gasta dinheiro e tempo. Fica no banco, e não em memória, porque cada Agent Skill roda
em um processo MCP próprio, que termina ao fim da chamada: um cache em memória nunca
seria reaproveitado em produção.

Guarda só o hash do texto, nunca o texto.
"""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.llm.security import content_sha256
from app.models import EmbeddingCacheEntry
from app.rag.base import EmbeddingProvider


class CachedEmbeddingProvider(EmbeddingProvider):
    def __init__(self, inner: EmbeddingProvider, db: Session, *, model: str) -> None:
        self.inner = inner
        self.db = db
        self.model = model
        self.name = inner.name

    def _lookup(self, hashes: list[str]) -> dict[str, list[float]]:
        rows = self.db.scalars(
            select(EmbeddingCacheEntry).where(
                EmbeddingCacheEntry.model == self.model, EmbeddingCacheEntry.text_hash.in_(hashes)
            )
        )
        return {row.text_hash: row.embedding for row in rows}

    def _store(self, text_hash: str, vector: list[float]) -> None:
        # Skills em paralelo podem gerar o mesmo vetor ao mesmo tempo: vale o primeiro.
        try:
            with self.db.begin_nested():
                self.db.add(EmbeddingCacheEntry(model=self.model, text_hash=text_hash, embedding=vector))
        except IntegrityError:
            pass

    def embed(self, texts: list[str]) -> list[list[float]]:
        hashes = [content_sha256(text) for text in texts]
        known = self._lookup(hashes)

        missing = [
            (text, text_hash) for text, text_hash in zip(texts, hashes, strict=True) if text_hash not in known
        ]
        if missing:
            unique = list(dict(missing).items())
            vectors = self.inner.embed([text for text, _ in unique])
            for (_, text_hash), vector in zip(unique, vectors, strict=True):
                known[text_hash] = vector
                self._store(text_hash, vector)

        return [known[text_hash] for text_hash in hashes]
