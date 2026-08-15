from pydantic import BaseModel, Field


class RetrievedChunk(BaseModel):
    chunk_id: str
    artifact_name: str
    content: str
    score: float
    metadata: dict = Field(default_factory=dict)


class RagContext(BaseModel):
    chunks: list[RetrievedChunk] = Field(default_factory=list)
    query: str
    retrieval_latency_ms: int | None = None

    def as_prompt_block(self) -> str | None:
        if not self.chunks:
            return None
        parts = []
        for chunk in self.chunks:
            parts.append(
                f"[{chunk.artifact_name}] (relevância {chunk.score:.2f})\n{chunk.content}"
            )
        return "\n\n".join(parts)
