"""
app/middleware/security_headers_middleware.py

CONFIG-001: Security headers middleware.

Injects browser-security response headers on every response:
  - X-Content-Type-Options: nosniff
  - X-Frame-Options: DENY
  - X-XSS-Protection: 1; mode=block
  - Referrer-Policy: strict-origin-when-cross-origin
  - Permissions-Policy: camera=(), microphone=(), geolocation=()
  - Strict-Transport-Security (production only)
  - Content-Security-Policy (production only)

These headers protect against:
  - MIME-sniffing attacks
  - Clickjacking via iframes
  - Reflected XSS
  - Referrer data leakage
  - Unwanted browser API access
  - Protocol downgrade attacks (HSTS)
"""

import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware that injects security headers into every HTTP response.
    Production-only headers (HSTS, CSP) are conditionally added
    based on APP_ENV to avoid breaking local development.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        response: Response = await call_next(request)

        # ── Always-on headers ─────────────────────────────────────────────
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=()"
        )

        # ── Deployment-only headers (Staging / Production) ────────────────
        if settings.is_deployed:
            # HSTS: enforce HTTPS for 1 year, including subdomains
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
            # CSP: restrict resource loading to same origin
            # Adjust as needed when adding CDN assets or external scripts
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data:; "
                "font-src 'self'; "
                "connect-src 'self'; "
                "frame-ancestors 'none'"
            )

        return response
