"""
app/core/events.py

Application lifecycle event handlers.
Registered in main.py via @app.on_event or lifespan context manager.

Security hardening:
  - Redis connectivity check at startup
  - Fail-fast in production if Redis is unavailable
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database.connection import check_db_connection, engine
from app.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _check_redis_connection() -> bool:
    """Verify Redis connectivity with retries and exponential backoff."""
    import time
    from app.core.redis_client import redis_client
    
    max_attempts = 1 if settings.is_development else 5
    backoff = 1.0  # start with 1 second delay
    
    for attempt in range(1, max_attempts + 1):
        try:
            if redis_client.ping():
                return True
        except Exception as exc:
            logger.warning(
                "Redis connection attempt %d/%d failed: %s. Retrying in %.1fs...",
                attempt, max_attempts, exc, backoff
            )
            if attempt == max_attempts:
                logger.error("Redis connection check failed after %d attempts: %s", max_attempts, exc)
                return False
            time.sleep(backoff)
            backoff *= 2
            
    return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles startup and shutdown events using the modern lifespan pattern.
    Passed directly to FastAPI() in main.py.
    """
    # ── STARTUP ───────────────────────────────────────────────────────────────
    logger.info("━━━ Starting %s [%s] ━━━", settings.APP_NAME, settings.APP_ENV)

    # Verify DB connectivity on boot
    if check_db_connection():
        logger.info("✓ Database connection established")
    else:
        logger.critical(
            "✗ Cannot connect to database at %s:%s — check your .env settings",
            settings.DB_HOST,
            settings.DB_PORT,
        )
        # In production, raise to prevent the server from starting broken
        if settings.is_production:
            raise RuntimeError("Database connection failed at startup")

    # Verify Redis connectivity on boot
    if _check_redis_connection():
        logger.info("✓ Redis connection established")
    else:
        logger.critical(
            "✗ Cannot connect to Redis at %s",
            settings.REDIS_URL,
        )
        # In production, Redis is critical (brute-force protection, token revocation, CSRF)
        if settings.is_production:
            raise RuntimeError(
                "Redis connection failed at startup. "
                "Redis is required for brute-force protection, token revocation, and session management."
            )
        else:
            logger.warning(
                "⚠ Redis is unavailable — brute-force protection and token revocation "
                "will not work. This is acceptable in development only."
            )

    # Log active storage backend
    logger.info("✓ Storage backend: %s", settings.STORAGE_BACKEND)

    logger.info("✓ %s is ready to serve requests", settings.APP_NAME)

    yield  # App runs here

    # ── SHUTDOWN ──────────────────────────────────────────────────────────────
    logger.info("Shutting down %s...", settings.APP_NAME)
    engine.dispose()
    logger.info("✓ Database connections closed")
