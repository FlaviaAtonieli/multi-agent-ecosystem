import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import SessionLocal
from app.core.middleware import (
    MaxBodySizeMiddleware,
    RequestIdMiddleware,
    SecurityHeadersMiddleware,
)
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
    logger.info("AgentHub backend started in %s mode", settings.environment)
    yield


app = FastAPI(
    title="AgentHub API",
    description="Secure foundation for the Agent Skills orchestration ecosystem.",
    version="0.1.0",
    lifespan=lifespan,
    # Auditoria de seguranca P1: Swagger/Redoc/schema nao ficam servidos em
    # producao, independente de a porta do backend estar ou nao acessivel
    # diretamente do host.
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
    openapi_url=None if settings.is_production else "/openapi.json",
)

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


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    payload = {"name": settings.app_name, "status": "online"}
    if app.docs_url:
        payload["docs"] = app.docs_url
    return payload


app.include_router(api_router, prefix=settings.api_v1_prefix)
