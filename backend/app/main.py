import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse, JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.openapi_docs import SWAGGER_CSRF_INTERCEPTOR, build_openapi
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import SessionLocal
from app.core.metrics import MetricsMiddleware, register_database_collector
from app.core.middleware import (
    MaxBodySizeMiddleware,
    RequestIdMiddleware,
    SecurityHeadersMiddleware,
)
from app.core.security import secure_compare
from app.db.init_db import bootstrap_admin, create_tables_if_enabled

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("agenthub")


@asynccontextmanager
async def lifespan(_: FastAPI):
    create_tables_if_enabled()
    with SessionLocal() as db:
        bootstrap_admin(db)
    logger.info("Flav.IA backend started in %s mode", settings.environment)
    yield


app = FastAPI(
    title="Flav.IA API",
    version="0.1.0",
    lifespan=lifespan,
    # Auditoria de seguranca P1: Swagger/Redoc/schema nao ficam servidos em
    # producao, independente de a porta do backend estar ou nao acessivel
    # diretamente do host. O schema exportado fica em docs/api/openapi.json.
    # /docs e servido pela rota swagger_ui abaixo (com o CSRF automatico).
    docs_url=None,
    redoc_url=None if settings.is_production else "/redoc",
    openapi_url=None if settings.is_production else "/openapi.json",
)
app.openapi = lambda: build_openapi(app)  # type: ignore[method-assign]

app.add_middleware(RequestIdMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.trusted_host_list,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-CSRF-Token", "X-Request-ID"],
)
if settings.metrics_enabled:
    register_database_collector()
    app.add_middleware(MetricsMiddleware)
# Added last so it runs first (Starlette wraps outward) -- rejects an
# oversized body via Content-Length before any other middleware or route
# handler touches the request.
app.add_middleware(MaxBodySizeMiddleware)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    message = exc.detail if isinstance(exc.detail, str) else "A solicitação não pôde ser processada."
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP_ERROR",
            "message": message,
            "request_id": getattr(request.state, "request_id", None),
        },
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    details = [
        {
            "field": ".".join(str(part) for part in error["loc"] if part != "body"),
            "message": error["msg"],
        }
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={
            "error": "VALIDATION_ERROR",
            "message": "Revise os dados informados.",
            "details": details,
            "request_id": getattr(request.state, "request_id", None),
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    logger.exception("Unhandled error. request_id=%s", request_id)
    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_ERROR",
            "message": "Ocorreu um erro interno. Use o identificador da requisição para suporte.",
            "request_id": request_id,
        },
    )


if not settings.is_production:

    @app.get("/docs", include_in_schema=False)
    def swagger_ui() -> HTMLResponse:
        page = get_swagger_ui_html(openapi_url="/openapi.json", title=f"{app.title} - Swagger")
        html = bytes(page.body).decode()
        # Injeta o requestInterceptor que copia o cookie CSRF para o cabeçalho,
        # para as rotas protegidas funcionarem direto pelo "Try it out".
        html = html.replace("SwaggerUIBundle({", "SwaggerUIBundle({\n  " + SWAGGER_CSRF_INTERCEPTOR, 1)
        return HTMLResponse(html)


if settings.metrics_enabled:

    @app.get("/metrics", include_in_schema=False)
    def metrics(request: Request) -> Response:
        """Scrape do Prometheus. Fora do prefixo /api, então o nginx do
        frontend não o expõe; com METRICS_TOKEN, exige Bearer token."""
        token = settings.metrics_token_value
        if token and not secure_compare(request.headers.get("Authorization", ""), f"Bearer {token}"):
            return JSONResponse(
                status_code=401,
                content={"error": "HTTP_ERROR", "message": "Token de métricas inválido."},
                headers={"WWW-Authenticate": "Bearer"},
            )
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    payload = {"name": settings.app_name, "status": "online"}
    if not settings.is_production:
        payload["docs"] = "/docs"
    return payload


app.include_router(api_router, prefix=settings.api_v1_prefix)
