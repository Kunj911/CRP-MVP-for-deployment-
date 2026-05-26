"""
app/core/redis_client.py

Redis connection pool for caching and JWT blacklisting.
"""

import redis
from redis.retry import Retry
from redis.backoff import ExponentialBackoff
from app.config.settings import get_settings

settings = get_settings()

_retry_strategy = Retry(
    backoff=ExponentialBackoff(cap=10, base=2),
    retries=3,
)

redis_client = redis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
    socket_timeout=2,
    socket_connect_timeout=2,
    retry=_retry_strategy,
    retry_on_timeout=True,
)

def get_redis():
    """Dependency for getting the Redis client."""
    return redis_client
