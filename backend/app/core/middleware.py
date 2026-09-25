from uuid import uuid4

from fastapi import Request, status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

from app.core.config import settings


class MaxBodySizeMiddleware(BaseHTTPMiddleware):
    """Auditoria de seguranca P2/P3 (correcao de 17/09/2026): rejeita um corpo de
    requisicao maior que MAX_REQUEST_BODY_BYTES -- antes de qualquer endpoint
    le-lo. A aplicacao so recebe JSON (sem upload de arquivo), entao o limite
    cobre folgadamente o maior payload legitimo hoje (contexto de solicitacao
    tecnica + listas do manifesto de uma skill).

    A primeira versao so checava o cabecalho Content-Length declarado -- uma
    requisicao com Transfer-Encoding: chunked (sem Content-Length, tamanho
    desconhecido ate o corpo terminar de chegar) passava direto, sem limite
    algum. Agora o corpo e lido em stream e contado byte a byte conforme
    chega, entao o limite vale independentemente de o cliente declarar (ou
    mentir sobre) o tamanho."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        limit = settings.max_request_body_bytes
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > limit:
                return JSONResponse(
                    status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                    content={
                        "error": "PAYLOAD_TOO_LARGE",
                        "message": "O corpo da requisição excede o tamanho máximo permitido.",
                    },
                )

        # request.stream() can only be drained once. Starlette's own
        # Request.body() caches into request._body after doing exactly this
        # same loop -- setting it here (instead of, say, replacing _receive)
        # is what makes BaseHTTPMiddleware's _CachedRequest replay the bytes
        # already read here to the downstream app, rather than an empty body.
        request._body = bytes(body)
        return await call_next(request)


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if request.url.path not in {"/docs", "/redoc"} and request.url.path != "/openapi.json":
            response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        if request.url.path.startswith(f"{settings.api_v1_prefix}/auth"):
            response.headers["Cache-Control"] = "no-store"
        if settings.cookie_secure:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response
