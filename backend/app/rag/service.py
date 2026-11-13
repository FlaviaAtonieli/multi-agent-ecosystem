import time

from sqlalchemy.orm import Session

from app.core.config import Settings, settings
from app.llm.schemas import LLMPlanRequest
from app.models import TechnicalRequest
from app.rag.factory import create_retriever
from app.rag.schemas import RagContext


def retrieve_context_for_request(
    db: Session,
    technical_request: TechnicalRequest,
    safe_request: LLMPlanRequest,
    *,
    config: Settings = settings,
) -> RagContext:
    # Proteção de contexto: com o domínio da skill, a busca puxa para a área dela em vez
    # de devolver o mesmo top-K para todas.
    query_parts = [safe_request.problem, safe_request.objective, safe_request.context]
    if safe_request.analysis_domain_label:
        query_parts.append(f"Domínio: {safe_request.analysis_domain_label}")
    query = " ".join(part for part in query_parts if part)

    if not config.rag_enabled or not query.strip():
        return RagContext(chunks=[], query=query)

    retriever = create_retriever(db, config)
    started = time.perf_counter()
    chunks = retriever.retrieve(query, top_k=config.rag_top_k, clan_id=technical_request.clan_id)
    latency_ms = round((time.perf_counter() - started) * 1000)

    return RagContext(chunks=chunks, query=query, retrieval_latency_ms=latency_ms)
