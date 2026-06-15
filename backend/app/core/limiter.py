"""
app/core/limiter.py

Global rate limiter instance using slowapi.
Uses X-Forwarded-For when behind a reverse proxy (Railway, Render, nginx).
"""

from fastapi import Request
from slowapi import Limiter

def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"

limiter = Limiter(key_func=_get_client_ip)
