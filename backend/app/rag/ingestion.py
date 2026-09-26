from sqlalchemy.orm import Session

from app.models import KnowledgeChunk
from app.rag.base import EmbeddingProvider


def chunk_text(content: str, *, max_chars: int, overlap: int) -> list[tuple[str, int, int]]:
    """Splits text into fixed-size, overlapping character windows.

    Returns a list of (chunk_content, char_start, char_end). A fixed-size window is
    enough for the PoC fixture (small synthetic legacy files); no NLP-aware chunking
    library is required.
    """
    if overlap >= max_chars:
        raise ValueError("overlap deve ser menor que max_chars")

    stripped = content.strip()
    if not stripped:
        return []

    chunks: list[tuple[str, int, int]] = []
    start = 0
    length = len(stripped)
    step = max_chars - overlap

    while start < length:
        end = min(start + max_chars, length)
        chunks.append((stripped[start:end], start, end))
        if end == length:
            break
        start += step

    return chunks


def ingest_artifact(
    db: Session,
    *,
    artifact_name: str,
    content: str,
    language: str | None,
    embedding_provider: EmbeddingProvider,
    source_type: str = "legacy_code_fixture",
    max_chars: int = 800,
    overlap: int = 100,
) -> list[KnowledgeChunk]:
    windows = chunk_text(content, max_chars=max_chars, overlap=overlap)
    if not windows:
        return []

    embeddings = embedding_provider.embed([window[0] for window in windows])

    chunks: list[KnowledgeChunk] = []
    for index, ((chunk_content, char_start, char_end), embedding) in enumerate(
        zip(windows, embeddings, strict=True)
    ):
        chunk = KnowledgeChunk(
            artifact_name=artifact_name,
            source_type=source_type,
            language=language,
            content=chunk_content,
            embedding=embedding,
            chunk_index=index,
            char_start=char_start,
            char_end=char_end,
        )
        db.add(chunk)
        chunks.append(chunk)

    db.flush()
    return chunks
