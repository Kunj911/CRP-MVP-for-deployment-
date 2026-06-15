"""
app/middleware/csrf_middleware.py

Double-submit CSRF protection middleware.

How it works:
  1. On login/refresh, the auth routes set a `csrf_token` cookie (non-HttpOnly).
  2. The frontend reads this cookie and sends it as an `X-CSRF-Token` header.
  3. This middleware validates that the header value matches the cookie value.

Protected methods: POST, PATCH, PUT, DELETE
Excluded paths: /auth/login (no existing session), /health, /docs, /openapi.json
Safe methods: GET, HEAD, OPTIONS (no side effects)

This prevents cross-site request forgery because:
  - A malicious site can trigger the browser to send cookies automatically
  - But it CANNOT read the csrf_token cookie (due to SameSite + Secure)
  - So it cannot set the X-CSRF-Token header
"""

import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Paths that don't need CSRF protection
_CSRF_EXEMPT_PATHS = {
    "/api/v1/auth/login",
    "/api/v1/auth/mfa/login-verify",
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
}

# Methods that don't need CSRF protection (they should have no side effects)
_SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


class CSRFMiddleware(BaseHTTPMiddleware):
    """
    Validates the double-submit CSRF token on state-changing requests.
    
    The csrf_token cookie is set by auth routes on login/refresh.
    The frontend must read it and send it as X-CSRF-Token header.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip CSRF for safe methods
        if request.method in _SAFE_METHODS:
            return await call_next(request)

        # Skip CSRF for exempt paths
        if request.url.path in _CSRF_EXEMPT_PATHS:
            return await call_next(request)

        # In development, optionally skip CSRF for easier testing
        if settings.is_development and not settings.DEBUG:
            pass  # Still enforce in dev — good practice

        # 1. Validate Origin / Referer against allowed domains (Task 8)
        origin = request.headers.get("Origin")
        if not origin:
            referer = request.headers.get("Referer")
            if referer:
                from urllib.parse import urlparse
                parsed = urlparse(referer)
                origin = f"{parsed.scheme}://{parsed.netloc}"

        if origin:
            origin = origin.rstrip("/")
            matched = False
            for allowed in settings.CORS_ORIGINS:
                if allowed == "*" or allowed.rstrip("/") == origin:
                    matched = True
                    break
            if not matched:
                logger.warning("CSRF Origin verification failed: '%s' not in CORS_ORIGINS", origin)
                return JSONResponse(
                    status_code=403,
                    content={
                        "success": False,
                        "error": {
                            "code": "CSRF_ORIGIN_MISMATCH",
                            "message": "Security validation failed: Request origin is untrusted.",
                        },
                    },
                )

        # 2. Get CSRF token from cookie and header
        cookie_token = request.cookies.get("csrf_token")
        header_token = request.headers.get("X-CSRF-Token")

        # If no CSRF cookie exists, this might be a request before login. Allow it through.
        if not cookie_token:
            return await call_next(request)

        # If cookie exists but header is missing or mismatched (using constant-time comparison) → reject (Task 7)
        import secrets
        if not header_token or not secrets.compare_digest(header_token, cookie_token):
            logger.warning(
                "CSRF validation failed: path=%s method=%s ip=%s "
                "cookie_present=%s header_present=%s",
                request.url.path,
                request.method,
                request.client.host if request.client else "unknown",
                bool(cookie_token),
                bool(header_token),
            )
            return JSONResponse(
                status_code=403,
                content={
                    "success": False,
                    "error": {
                        "code": "CSRF_VALIDATION_FAILED",
                        "message": "CSRF token validation failed. Please refresh the page and try again.",
                    },
                },
            )

        return await call_next(request)
