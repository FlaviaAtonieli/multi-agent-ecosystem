from pathlib import Path

from sqlalchemy import func, select

from app.core.config import settings
from app.core.database import SessionLocal
from app.models import KnowledgeChunk
from app.rag.factory import create_embedding_provider
from app.rag.ingestion import ingest_artifact

FIXTURES_ROOT = Path(__file__).resolve().parent.parent / "rag" / "fixtures"

_LANGUAGE_BY_SUFFIX = {
    ".java": "java",
    ".sql": "sql",
    ".md": "markdown",
}


def seed_knowledge_base() -> None:
    """Indexa todos os domínios de app/rag/fixtures/ na mesma tabela knowledge_chunks.

    A busca não filtra por domínio, então cada área precisa da própria evidência
    indexada para ser favorecida em relação às outras.
    """
    embedding_provider = create_embedding_provider(settings)

    with SessionLocal() as db:
        existing = db.scalar(select(func.count(KnowledgeChunk.id)))
        if existing:
            print(f"knowledge_chunks já populada ({existing} chunks). Nada a fazer.")
            return

        for domain_dir in sorted(FIXTURES_ROOT.iterdir()):
            if not domain_dir.is_dir():
                continue

            for path in sorted(domain_dir.glob("*")):
                if not path.is_file():
                    continue

                content = path.read_text(encoding="utf-8")
                chunks = ingest_artifact(
                    db,
                    artifact_name=path.name,
                    source_type=f"{domain_dir.name}_fixture",
                    language=_LANGUAGE_BY_SUFFIX.get(path.suffix),
                    content=content,
                    embedding_provider=embedding_provider,
                    max_chars=settings.rag_chunk_max_chars,
                    overlap=settings.rag_chunk_overlap,
                )
                print(f"{domain_dir.name}/{path.name}: {len(chunks)} chunks indexados")

        db.commit()


if __name__ == "__main__":
    seed_knowledge_base()
