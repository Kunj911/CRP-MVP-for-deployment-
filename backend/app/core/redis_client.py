"""
app/core/redis_client.py

Redis connection pool for caching and JWT blacklisting.
Includes timeout configurations, retry strategy, and graceful failure handling.

Railway: REDIS_URL is injected automatically.
Falls back to redis://localhost:6379/0 for local development.
"""

import redis
import logging
from redis.retry import Retry
from redis.backoff import ExponentialBackoff
from app.core.config import get_settings

logger = logging.getLogger("livetrace.redis")
settings = get_settings()

class SafeRedisPipeline:
    """Mock Redis Pipeline to degrade gracefully if Redis is offline."""
    def __getattr__(self, name):
        def wrapper(*args, **kwargs):
            if name == "execute":
                return [0, True, 0, True]  # Mock return values for standard operations
            return self
        return wrapper

class SafeRedis:
    """Wrapper around Redis client to catch exceptions and degrade gracefully."""
    def __init__(self, client):
        self._client = client

    def __getattr__(self, name):
        val = getattr(self._client, name)
        if callable(val):
            def wrapper(*args, **kwargs):
                try:
                    return val(*args, **kwargs)
                except Exception as e:
                    logger.warning(
                        f"Redis error during '{name}' operation: {e}. Degrading gracefully."
                    )
                    if name == "pipeline":
                        return SafeRedisPipeline()
                    if name == "ping":
                        return False
                    return None
            return wrapper
        return val


class LazyRedis:
    """
    Reconnect lazily instead of permanently degrading when Redis is not ready at import time.
    """
    def __init__(self):
        self._client = None

    def _connect(self):
        retry_strategy = Retry(
            backoff=ExponentialBackoff(cap=10, base=2),
            retries=3,
        )
        raw_client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_timeout=5,
            socket_connect_timeout=5,
            retry=retry_strategy,
            retry_on_timeout=True,
        )
        raw_client.ping()
        logger.info(
            "Redis client connected to %s",
            settings.REDIS_URL.split("@")[-1] if "@" in settings.REDIS_URL else settings.REDIS_URL,
        )
        self._client = SafeRedis(raw_client)
        return self._client

    def __getattr__(self, name):
        def wrapper(*args, **kwargs):
            try:
                client = self._client or self._connect()
                return getattr(client, name)(*args, **kwargs)
            except Exception as exc:
                logger.warning(
                    "Redis error during '%s' operation: %s. Degrading gracefully.",
                    name,
                    exc,
                )
                self._client = None
                if name == "pipeline":
                    return SafeRedisPipeline()
                if name == "ping":
                    return False
                if name == "get":
                    return None
                if name == "execute":
                    return []
                return None
        return wrapper


redis_client = LazyRedis()

def get_redis():
    """Dependency for getting the Redis client."""
    return redis_client
