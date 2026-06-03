"""
app/core/redis_client.py

Redis connection pool for caching and JWT blacklisting.
Includes timeout configurations, retry strategy, and graceful failure handling.
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


# Configure robust retry strategy
_retry_strategy = Retry(
    backoff=ExponentialBackoff(cap=10, base=2),
    retries=3,
)

# Connect with recommended timeouts (socket_timeout=5, socket_connect_timeout=5)
_raw_client = redis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
    socket_timeout=5,
    socket_connect_timeout=5,
    retry=_retry_strategy,
    retry_on_timeout=True,
)

redis_client = SafeRedis(_raw_client)

def get_redis():
    """Dependency for getting the Redis client."""
    return redis_client
