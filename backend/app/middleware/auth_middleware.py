"""
app/middleware/auth_middleware.py

Optional Starlette-level JWT authentication middleware.

NOTE: For most routes, use the FastAPI dependency injection approach
(get_current_user in deps.py) — it's more idiomatic and testable.

This middleware is useful when you need to:
  - Attach user context globally to request.state for logging
  - Enforce auth at the middleware level (e.g. for WebSocket routes)
  - Read token info before the route handler runs

Public paths (no auth required) are explicitly whitelisted below.
"""

import logging
from typing import Set

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.security import decode_access_token
from app.core.exceptions import UnauthorizedException

logger = logging.getLogger(__name__)

# ── Paths that do NOT require authentication ──────────────────────────────────
PUBLIC_PATHS: Set[str] = {
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/favicon.ico",
    "/api/v1/auth/login",
    "/api/v1/auth/refresh",
}


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware that:
    1. Skips auth for public paths
    2. Decodes the JWT and attaches user_id + role to request.state
    3. Does NOT block the request — route-level deps handle 401/403

    This means request.state.user_id and request.state.role are available
    in route handlers and other middleware without a DB query.
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip public paths
        if request.url.path in PUBLIC_PATHS:
            return await call_next(request)

        # Try to decode token and attach to state (best-effort, no hard fail)
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            try:
                payload = decode_access_token(token)
                request.state.user_id = payload.get("sub")
                request.state.user_role = payload.get("role")
            except Exception:
                # Don't block here — let route deps raise 401 with proper response
                request.state.user_id = None
                request.state.user_role = None
        else:
            request.state.user_id = None
            request.state.user_role = None

        return await call_next(request)
