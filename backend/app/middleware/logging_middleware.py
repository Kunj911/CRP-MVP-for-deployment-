"""
app/middleware/logging_middleware.py

Structured request/response logging middleware.
Logs method, path, status code, and response time for every request.
Skips noisy endpoints like /health.
"""

import logging
import time
import uuid

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("livetrace.requests")

# Endpoints to skip logging (too noisy)
_SKIP_PATHS = {"/health", "/favicon.ico", "/docs", "/openapi.json", "/redoc"}


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in _SKIP_PATHS:
            return await call_next(request)

        # Attach a unique request ID for tracing across logs
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id

        start = time.perf_counter()

        logger.info(
            "→ [%s] %s %s",
            request_id,
            request.method,
            request.url.path,
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query": str(request.query_params),
                "client_ip": request.client.host if request.client else "unknown",
            },
        )

        response: Response = await call_next(request)

        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        log_fn = logger.warning if response.status_code >= 400 else logger.info
        log_fn(
            "← [%s] %s %s — %d (%sms)",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            extra={
                "request_id": request_id,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )

        # Attach request ID to response headers for client-side tracing
        response.headers["X-Request-ID"] = request_id
        return response
