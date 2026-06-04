"""
main.py

Live-Trace FastAPI application entry point.

Responsibilities:
    - Create the FastAPI app instance
    - Register middleware (order matters — outermost first)
    - Mount the v1 API router
    - Register global exception handlers
    - Define the /health endpoint
    - Configure OpenAPI docs

Security hardening:
    - CSRF middleware for double-submit protection
    - X-CSRF-Token added to CORS allowed headers
    - Redis health included in /health endpoint

Run with:
    uvicorn main:app --reload              # development
    uvicorn main:app --host 0.0.0.0 --port 8000  # production
"""

import logging
import logging.config
import secrets
from typing import Any

from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from app.core.limiter import limiter

from app.api.v1 import api_router
from app.core.events import lifespan
from app.core.exceptions import LiveTraceException
from app.database.connection import check_db_connection
from app.middleware.logging_middleware import LoggingMiddleware
from app.config.settings import get_settings

settings = get_settings()


# ── Logging setup ─────────────────────────────────────────────────────────────

def configure_logging() -> None:
    """
    Configure structured logging.
    In production, swap the formatter to pythonjsonlogger.JsonFormatter
    for log aggregation tools (Datadog, CloudWatch, etc.)
    """
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO

    if settings.is_production:
        formatter_config = {
            "class": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        }
    else:
        formatter_config = {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        }

    logging.config.dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": formatter_config,
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "standard",
                "stream": "ext://sys.stdout",
            },
        },
        "root": {
            "level": log_level,
            "handlers": ["console"],
        },
        # Silence noisy third-party loggers in production
        "loggers": {
            "uvicorn.access": {"level": "WARNING" if not settings.DEBUG else "INFO"},
            "sqlalchemy.engine": {"level": "WARNING" if not settings.DEBUG else "INFO"},
        },
    })


configure_logging()
logger = logging.getLogger(__name__)


# ── Metrics Auth Dependency ───────────────────────────────────────────────────

security = HTTPBasic()

def get_metrics_user(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    correct_username = secrets.compare_digest(credentials.username, "prometheus")
    correct_password = secrets.compare_digest(credentials.password, settings.METRICS_PASSWORD)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect metrics credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


# ── App factory ───────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        description="B2B Supply Chain Transparency Platform for Agricultural Commodity Exporters",
        version="1.0.0",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # Initialize Sentry (Task 14)
    if settings.SENTRY_DSN:
        try:
            import sentry_sdk
            sentry_sdk.init(
                dsn=settings.SENTRY_DSN,
                environment=settings.APP_ENV,
                traces_sample_rate=1.0 if settings.is_development else 0.1,
            )
            logger.info("✓ Sentry SDK initialized")
        except ImportError:
            logger.warning("sentry-sdk package not installed — Sentry integration skipped")

    # Expose Prometheus Metrics (Task 14)
    if settings.PROMETHEUS_METRICS_ENABLED:
        try:
            from prometheus_fastapi_instrumentator import Instrumentator
            Instrumentator().instrument(app).expose(
                app,
                tags=["Observability"],
                dependencies=[Depends(get_metrics_user)],
            )
            logger.info("✓ Prometheus metrics endpoint enabled at /metrics")
        except ImportError:
            logger.warning("prometheus-fastapi-instrumentator not installed — metrics skipped")

    app.state.limiter = limiter

    _register_middleware(app)
    _register_exception_handlers(app)
    _register_routes(app)

    # Mount static uploads directory if using local storage
    if settings.STORAGE_BACKEND == "local":
        from fastapi.staticfiles import StaticFiles
        import os
        os.makedirs(settings.LOCAL_UPLOAD_DIR, exist_ok=True)
        app.mount("/uploads", StaticFiles(directory=settings.LOCAL_UPLOAD_DIR), name="uploads")

    return app


# ── Middleware ────────────────────────────────────────────────────────────────
# Registration order = outermost wrapper first.
# Request path:  CORS → Security Headers → CSRF → HTTPS Redirect → Logging → [route handler]
# Response path: [route handler] → Logging → HTTPS Redirect → CSRF → Security Headers → CORS

def _register_middleware(app: FastAPI) -> None:
    # 1. CORS — must be outermost so preflight requests are handled first
    # CONFIG-003: Tightened methods and headers for security
    # Added X-CSRF-Token to allowed headers for double-submit CSRF pattern
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-CSRF-Token"],
        expose_headers=["X-Request-ID"],
    )

    # 2. CONFIG-001: Security headers (X-Content-Type-Options, X-Frame-Options, etc.)
    from app.middleware.security_headers_middleware import SecurityHeadersMiddleware
    app.add_middleware(SecurityHeadersMiddleware)

    # 3. CSRF: Double-submit cookie validation for state-changing requests
    from app.middleware.csrf_middleware import CSRFMiddleware
    app.add_middleware(CSRFMiddleware)

    # 4. CONFIG-002: HTTPS redirect in production only
    if settings.is_production:
        from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
        app.add_middleware(HTTPSRedirectMiddleware)

    # 5. Request / response logging with timing and request IDs
    app.add_middleware(LoggingMiddleware)


# ── Exception handlers ────────────────────────────────────────────────────────

def _register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    @app.exception_handler(LiveTraceException)
    async def livetrace_exception_handler(
        request: Request, exc: LiveTraceException
    ) -> JSONResponse:
        """Convert all LiveTraceExceptions into the standard error envelope."""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": exc.error_code,
                    "message": exc.detail,
                },
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """
        Catch-all for unexpected errors.
        Logs the full traceback; returns a safe generic message to clients.
        """
        request_id = getattr(request.state, "request_id", "unknown")
        logger.exception(
            "Unhandled exception on [%s] %s [request_id=%s]",
            request.method,
            request.url.path,
            request_id,
        )
        if settings.SENTRY_DSN:
            try:
                import sentry_sdk
                sentry_sdk.capture_exception(exc)
            except Exception as e:
                logger.error("Failed to capture exception in Sentry: %s", e)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": {
                    "code": "SERVER_ERROR",
                    "message": "An unexpected error occurred. Please try again later.",
                },
            },
        )


# ── Routes ────────────────────────────────────────────────────────────────────

def _check_redis_health() -> bool:
    """Check Redis connectivity for health endpoint."""
    try:
        from app.core.redis_client import redis_client
        return redis_client.ping()
    except Exception:
        return False


def _register_routes(app: FastAPI) -> None:
    # Health check — no auth, no DB required, used by load balancers + Render
    @app.get("/health", tags=["System"], include_in_schema=False)
    def health_check() -> dict[str, Any]:
        db_ok = check_db_connection()
        redis_ok = _check_redis_health()
        
        if db_ok and redis_ok:
            status = "ok"
        elif db_ok or redis_ok:
            status = "degraded"
        else:
            status = "unhealthy"
        
        return {
            "status": status,
            "app": settings.APP_NAME,
            "env": settings.APP_ENV,
            "database": "connected" if db_ok else "unreachable",
            "redis": "connected" if redis_ok else "unreachable",
            "storage_backend": settings.STORAGE_BACKEND,
        }

    # Mount all v1 API routes
    app.include_router(api_router, prefix="/api/v1")


# ── Entry point ───────────────────────────────────────────────────────────────

app = create_app()
