"""Métricas Prometheus do backend, expostas em GET /metrics.

Três grupos:

- HTTP (middleware): requisições por rota/status, latência e em andamento. A
  rota é o template ("/api/v1/requests/{request_id}"), nunca a URL concreta,
  para não explodir a cardinalidade.
- Domínio (instrumentado nos serviços): chamadas ao LLM e tokens, execuções de
  Agent Skills, veredito do Quality Gate, revisões humanas e eventos de
  auditoria (login, falhas de login, código por e-mail, redefinição de senha).
- Estado do banco (coletado a cada scrape): solicitações por status, Agent
  Skills ativas, usuários e clãs.
"""

import logging
import time
from collections.abc import Iterator

from fastapi import Request
from prometheus_client import Counter, Gauge, Histogram, Info
from prometheus_client.core import REGISTRY, GaugeMetricFamily
from prometheus_client.registry import Collector
from sqlalchemy import func, select
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response
from starlette.routing import Match

from app.core.config import settings

logger = logging.getLogger(__name__)

HTTP_REQUESTS = Counter(
    "agenthub_http_requests_total", "Requisições HTTP atendidas.", ["method", "route", "status"]
)
HTTP_LATENCY = Histogram(
    "agenthub_http_request_duration_seconds",
    "Duração das requisições HTTP.",
    ["method", "route"],
    # Vai até 5 min: a execução da orquestração chama o LLM várias vezes.
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60, 120, 300),
)
HTTP_IN_PROGRESS = Gauge("agenthub_http_requests_in_progress", "Requisições HTTP em andamento.")

LLM_INVOCATIONS = Counter(
    "agenthub_llm_invocations_total", "Chamadas ao provedor de LLM.", ["provider", "model", "status"]
)
LLM_LATENCY = Histogram(
    "agenthub_llm_invocation_duration_seconds",
    "Duração das chamadas ao LLM.",
    ["provider", "model"],
    buckets=(0.5, 1, 2, 5, 10, 20, 30, 45, 60, 90, 120),
)
LLM_TOKENS = Counter(
    "agenthub_llm_tokens_total", "Tokens consumidos no LLM.", ["provider", "model", "direction"]
)

SKILL_INVOCATIONS = Counter(
    "agenthub_agent_skill_invocations_total", "Execuções de Agent Skills.", ["domain", "status"]
)
SKILL_LATENCY = Histogram(
    "agenthub_agent_skill_invocation_duration_seconds",
    "Duração das execuções de Agent Skills.",
    ["domain"],
    buckets=(0.5, 1, 2, 5, 10, 20, 30, 45, 60, 90, 120),
)
QUALITY_GATE_VERDICTS = Counter(
    "agenthub_quality_gate_verdicts_total",
    "Vereditos do Conselheiro (Quality Gate): approved ou human_review.",
    ["outcome"],
)
HUMAN_REVIEWS = Counter("agenthub_human_reviews_total", "Decisões de revisão humana.", ["decision"])
AUDIT_EVENTS = Counter(
    "agenthub_audit_events_total",
    "Eventos de auditoria (login, falha de login, código por e-mail, redefinição de senha...).",
    ["event_type"],
)

APP_INFO = Info("agenthub_app", "Versão e ambiente do backend.")
APP_INFO.info({"version": "0.1.0", "environment": settings.environment})


def _route_template(request: Request) -> str:
    """Template da rota que atende a requisição, ou "unmatched" (404 de rota
    inexistente) -- assim varreduras de URL não criam séries novas."""
    for route in request.app.router.routes:
        match, _ = route.matches(request.scope)
        if match == Match.FULL:
            return getattr(route, "path", "unmatched")
    return "unmatched"


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path == "/metrics":
            return await call_next(request)

        method = request.method
        HTTP_IN_PROGRESS.inc()
        started = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            HTTP_IN_PROGRESS.dec()
            route = request.scope.get("route")
            template = getattr(route, "path", None) or _route_template(request)
            # Rotas de roteadores incluídos guardam o caminho sem o prefixo de
            # include_router; toda a API vive sob API_V1_PREFIX.
            prefix = settings.api_v1_prefix
            in_api = request.url.path.startswith(prefix)
            if in_api and template != "unmatched" and not template.startswith(prefix):
                template = f"{prefix}{template}"
            HTTP_REQUESTS.labels(method, template, str(status_code)).inc()
            HTTP_LATENCY.labels(method, template).observe(time.perf_counter() - started)


class DatabaseStateCollector(Collector):
    """Lê o estado atual do banco a cada scrape (consultas de contagem, baratas
    nesta escala). Falha do banco não derruba o /metrics: só omite estas séries."""

    def describe(self) -> Iterator[GaugeMetricFamily]:
        # Sem isto, REGISTRY.register() chamaria collect() na importação --
        # consultando o banco antes de as tabelas existirem.
        return iter(())

    def collect(self) -> Iterator[GaugeMetricFamily]:
        from app.core.database import SessionLocal
        from app.models import AgentSkill, Clan, TechnicalRequest, User

        try:
            with SessionLocal() as db:
                requests_by_status = db.execute(
                    select(TechnicalRequest.status, func.count()).group_by(TechnicalRequest.status)
                ).all()
                active_skills = db.scalar(
                    select(func.count(AgentSkill.id)).where(
                        AgentSkill.enabled.is_(True), AgentSkill.status == "approved"
                    )
                )
                users = db.scalar(select(func.count(User.id)))
                clans = db.scalar(select(func.count(Clan.id)))
        except Exception as exc:  # noqa: BLE001 - métricas nunca devem quebrar o scrape
            logger.warning("Não foi possível coletar métricas do banco: %s", type(exc).__name__)
            return

        by_status = GaugeMetricFamily(
            "agenthub_technical_requests", "Solicitações técnicas por status.", labels=["status"]
        )
        for status, count in requests_by_status:
            by_status.add_metric([status], count)
        yield by_status
        yield GaugeMetricFamily(
            "agenthub_agent_skills_active", "Agent Skills ativas no catálogo.", value=active_skills or 0
        )
        yield GaugeMetricFamily("agenthub_users", "Usuários cadastrados.", value=users or 0)
        yield GaugeMetricFamily("agenthub_clans", "Clãs criados.", value=clans or 0)


_collector_registered = False


def register_database_collector() -> None:
    global _collector_registered
    if not _collector_registered:
        REGISTRY.register(DatabaseStateCollector())
        _collector_registered = True
