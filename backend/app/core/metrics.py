"""Métricas Prometheus do backend, expostas em GET /metrics.

Três grupos:

- HTTP (middleware): requisições por rota/status, latência e em andamento. A
  rota é o template ("/api/v1/requests/{request_id}"), nunca a URL concreta,
  para não explodir a cardinalidade.
- Domínio (instrumentado nos serviços): execuções de Agent Skills, veredito do
  Quality Gate, revisões humanas e eventos de auditoria (login, falhas de login,
  código por e-mail, redefinição de senha).
- Banco (coletado a cada scrape): solicitações por status, Agent Skills ativas,
  usuários, comitês e o uso do LLM. O LLM é chamado dentro do processo de cada skill
  (MCP por stdio), que termina ao fim da chamada: um contador em memória lá nunca
  chegaria a este /metrics. A tabela llm_invocations já registra cada chamada.
"""

import logging
import time
from collections.abc import Iterator, Sequence
from typing import Any

from fastapi import Request
from prometheus_client import Counter, Gauge, Histogram, Info
from prometheus_client.core import (
    REGISTRY,
    CounterMetricFamily,
    GaugeMetricFamily,
    HistogramMetricFamily,
)
from prometheus_client.metrics_core import Metric
from prometheus_client.registry import Collector
from sqlalchemy import case, func, select
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

_LLM_LATENCY_BUCKETS = (0.5, 1, 2, 5, 10, 20, 30, 45, 60, 90, 120)
_LLM_FINISHED_STATUSES = ("COMPLETED", "FAILED")

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


def _llm_usage_metrics(rows: Sequence[Any]) -> Iterator[Metric]:
    """Monotônico porque vem de uma contagem no banco, então `increase()` funciona
    como em um contador comum, e os valores sobrevivem a um reinício do backend."""
    invocations = CounterMetricFamily(
        "agenthub_llm_invocations", "Chamadas ao provedor de LLM.", labels=["provider", "model", "status"]
    )
    tokens = CounterMetricFamily(
        "agenthub_llm_tokens", "Tokens consumidos no LLM.", labels=["provider", "model", "direction"]
    )
    latency = HistogramMetricFamily(
        "agenthub_llm_invocation_duration_seconds",
        "Duração das chamadas ao LLM.",
        labels=["provider", "model"],
    )

    token_totals: dict[tuple[str, str], list[float]] = {}
    latency_totals: dict[tuple[str, str], list[float]] = {}
    for provider, model, status, count, input_tokens, output_tokens, latency_sum, *buckets in rows:
        invocations.add_metric([provider, model, status], count)

        totals = token_totals.setdefault((provider, model), [0, 0])
        totals[0] += input_tokens or 0
        totals[1] += output_tokens or 0

        # [total de chamadas, soma das latências, contagem acumulada por bucket]
        aggregate = latency_totals.setdefault((provider, model), [0, 0, *[0] * len(_LLM_LATENCY_BUCKETS)])
        aggregate[0] += count
        aggregate[1] += latency_sum or 0
        for index, bucket_count in enumerate(buckets):
            aggregate[index + 2] += bucket_count or 0

    for (provider, model), (input_total, output_total) in token_totals.items():
        tokens.add_metric([provider, model, "input"], input_total)
        tokens.add_metric([provider, model, "output"], output_total)
    for (provider, model), (total, latency_sum, *cumulative) in latency_totals.items():
        histogram = [
            (str(float(bucket)), value)
            for bucket, value in zip(_LLM_LATENCY_BUCKETS, cumulative, strict=True)
        ]
        latency.add_metric([provider, model], [*histogram, ("+Inf", total)], sum_value=latency_sum)

    yield invocations
    yield tokens
    yield latency


class DatabaseStateCollector(Collector):
    """Lê o estado atual do banco a cada scrape (consultas de contagem, baratas
    nesta escala). Falha do banco não derruba o /metrics: só omite estas séries."""

    def describe(self) -> Iterator[Metric]:
        # Sem isto, REGISTRY.register() chamaria collect() na importação --
        # consultando o banco antes de as tabelas existirem.
        return iter(())

    def collect(self) -> Iterator[Metric]:
        from app.core.database import SessionLocal
        from app.models import AgentSkill, Clan, LLMInvocation, TechnicalRequest, User

        latency_seconds = LLMInvocation.latency_ms / 1000.0
        bucket_counts = [
            func.sum(case((latency_seconds <= bucket, 1), else_=0)) for bucket in _LLM_LATENCY_BUCKETS
        ]

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
                llm_usage = db.execute(
                    select(
                        LLMInvocation.provider,
                        LLMInvocation.model,
                        LLMInvocation.status,
                        func.count(),
                        func.sum(LLMInvocation.input_tokens),
                        func.sum(LLMInvocation.output_tokens),
                        func.sum(latency_seconds),
                        *bucket_counts,
                    )
                    .where(LLMInvocation.status.in_(_LLM_FINISHED_STATUSES))
                    .group_by(LLMInvocation.provider, LLMInvocation.model, LLMInvocation.status)
                ).all()
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
        yield GaugeMetricFamily("agenthub_clans", "Comitês criados.", value=clans or 0)
        yield from _llm_usage_metrics(llm_usage)


_collector_registered = False


def register_database_collector() -> None:
    global _collector_registered
    if not _collector_registered:
        REGISTRY.register(DatabaseStateCollector())
        _collector_registered = True
