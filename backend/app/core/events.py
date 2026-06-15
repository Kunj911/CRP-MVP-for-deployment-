"""
app/core/events.py

Application lifecycle event handlers.
Registered in main.py via @app.on_event or lifespan context manager.

Startup validation:
  - Database connectivity is MANDATORY in staging and production.
  - Redis is configurable via REDIS_REQUIRED setting.
  - Development mode allows startup with warnings.
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


def _redact_url(url: str) -> str:
    """Redact password from a database/redis URL for safe logging."""
    import re
    redacted = re.sub(r'://([^:]+):([^@]+)@', r'://\1:***@', url)
    if redacted == url:
        redacted = re.sub(r'://:([^@]+)@', r'://:***@', url)
    return redacted


def _verify_and_initialize_schema(db_engine) -> None:
    """
    Check if the database schema is initialized (specifically looking for the 'users' table).
    If missing, initialize the schema using Base.metadata.create_all.
    This guarantees that staging boots successfully on an empty MySQL database.
    """
    from sqlalchemy import inspect
    
    try:
        inspector = inspect(db_engine)
        tables = inspector.get_table_names()
        
        import app.models
        from app.database.connection import Base

        expected_tables = set(Base.metadata.tables.keys())
        existing_tables = set(tables)
        missing_tables = sorted(expected_tables - existing_tables)

        if missing_tables:
            logger.info("Database schema is missing tables %s. Initializing schema...", missing_tables)
            Base.metadata.create_all(bind=db_engine)
            logger.info("[OK] Database schema initialized successfully.")
        else:
            logger.info("[OK] Database schema already initialized ('users' table present). Skipping initialization.")
    except Exception as exc:
        logger.error("Failed to verify/initialize database schema: %s", exc)
        if settings.is_deployed:
            raise RuntimeError(
                f"Database schema initialization failed: {exc}. "
                f"Ensure the database URL is correct and the user has DDL permissions."
            )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles startup and shutdown events using the modern lifespan pattern.
    Passed directly to FastAPI() in main.py.
    
    Startup validation behavior:
      - development: warn on failures, continue startup
      - staging: FAIL on database unavailable, configurable Redis
      - production: FAIL on database unavailable, configurable Redis
    """
    # ── STARTUP ───────────────────────────────────────────────────────────────
    logger.info("=== Starting %s [%s] ===", settings.APP_NAME, settings.APP_ENV)
    logger.info("Database URL: %s", _redact_url(settings.DATABASE_URL))

    # Verify DB connectivity on boot
    if check_db_connection():
        logger.info("[OK] Database connection established")
        _verify_and_initialize_schema(engine)
    else:
        logger.critical(
            "[FAIL] Cannot connect to database - URL: %s",
            _redact_url(settings.DATABASE_URL),
        )
        # In staging and production, raise to prevent the server from starting broken
        if settings.is_deployed:
            raise RuntimeError(
                f"Database connection failed at startup in '{settings.APP_ENV}' environment. "
                f"Verify DB_HOST, DB_PORT, DB_NAME, DB_USER, and DB_PASSWORD are set correctly."
            )
        else:
            logger.warning(
                "[WARN] Database unavailable - continuing in development mode. "
                "API routes requiring database will fail."
            )

    # Verify Redis connectivity on boot
    if _check_redis_connection():
        logger.info("[OK] Redis connection established")
    else:
        logger.warning(
            "[FAIL] Cannot connect to Redis at %s",
            _redact_url(settings.REDIS_URL),
        )
        # Redis failure behavior depends on REDIS_REQUIRED setting
        if settings.REDIS_REQUIRED:
            raise RuntimeError(
                f"Redis connection failed at startup (REDIS_REQUIRED=True). "
                f"Redis is required for brute-force protection, token revocation, and session management. "
                f"Verify REDIS_URL is set correctly."
            )
        elif settings.is_deployed:
            logger.warning(
                "[WARN] Redis is unavailable in '%s' environment - brute-force protection "
                "and token revocation will degrade. Set REDIS_REQUIRED=True to enforce.",
                settings.APP_ENV,
            )
        else:
            logger.warning(
                "[WARN] Redis is unavailable - brute-force protection and token revocation "
                "will not work. This is acceptable in development only."
            )

    # Log active storage backend
    logger.info("[OK] Storage backend: %s", settings.STORAGE_BACKEND)

    logger.info("[OK] %s is ready to serve requests", settings.APP_NAME)

    yield  # App runs here

    # ── SHUTDOWN ──────────────────────────────────────────────────────────────
    logger.info("Shutting down %s...", settings.APP_NAME)
    engine.dispose()
    logger.info("[OK] Database connections closed")
    try:
        from app.core.redis_client import redis_client
        redis_client.close()
        logger.info("[OK] Redis connections closed")
    except Exception:
        pass
