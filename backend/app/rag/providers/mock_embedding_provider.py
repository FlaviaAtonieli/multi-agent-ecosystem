import hashlib
import math
import re

from app.rag.base import EmbeddingProvider

_TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9_À-ÿ]+")
_EMBEDDING_DIM = 256


def _token_dimension(token: str) -> int:
    # sha256 (not the builtin hash()) keeps this deterministic across runs,
    # since PYTHONHASHSEED randomizes str hashing by default.
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return int(digest, 16) % _EMBEDDING_DIM


class MockEmbeddingProvider(EmbeddingProvider):
    """Deterministic, hashing-based bag-of-words embedding.

    No network calls and no external dependency, mirroring MockLLMProvider's
    role: lets retrieval run fully offline in tests and CI.
    """

    name = "mock"

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        vector = [0.0] * _EMBEDDING_DIM
        for token in _TOKEN_PATTERN.findall(text.lower()):
            vector[_token_dimension(token)] += 1.0

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]
