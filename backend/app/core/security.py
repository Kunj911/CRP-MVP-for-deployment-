"""
app/core/security.py

JWT token creation / decoding and password hashing.
Used exclusively by auth_service — never imported into routes.

Security hardening:
  - hash_token(): SHA-256 hash for refresh tokens before DB storage
  - Refresh tokens are treated like passwords — never stored in plaintext
"""

import hashlib
from datetime import UTC, datetime, timedelta
from typing import Any
import uuid

import bcrypt
from jose import JWTError, jwt

from app.core.exceptions import TokenExpiredException, UnauthorizedException
from app.core.redis_client import redis_client
from app.config.settings import get_settings

settings = get_settings()

# ── Password hashing ──────────────────────────────────────────────────────────


def _prepare_password(password: str) -> bytes:
    """
    Trim whitespace, encode to UTF-8, and truncate to 72 bytes (the bcrypt limit).
    Returns a bytes object suitable for bcrypt.
    """
    trimmed = password.strip()
    return trimmed.encode("utf-8")[:72]


def hash_password(plain_password: str) -> str:
    """Return a bcrypt hash of the given password."""
    pw_bytes = _prepare_password(plain_password)
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pw_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return True if the plain password matches the hash."""
    try:
        pw_bytes = _prepare_password(plain_password)
        hash_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(pw_bytes, hash_bytes)
    except Exception:
        return False


# ── Token hashing (for refresh tokens) ────────────────────────────────────────

def hash_token(token: str) -> str:
    """
    Return a SHA-256 hex digest of the given token.

    Used for refresh tokens before DB storage. SHA-256 (not bcrypt) is
    appropriate here because refresh tokens are high-entropy random JWTs,
    making brute-force infeasible even without a slow hash.
    """
    return hashlib.sha256(token.encode()).hexdigest()


# ── JWT ───────────────────────────────────────────────────────────────────────

def _create_token(data: dict[str, Any], expires_delta: timedelta) -> str:
    """Internal helper — create a signed JWT with an expiry claim."""
    payload = data.copy()
    payload["exp"] = datetime.now(UTC) + expires_delta
    payload["iat"] = datetime.now(UTC)
    payload["jti"] = str(uuid.uuid4())
    # Sign with the first (primary) secret key in the list
    return jwt.encode(
        payload,
        settings.JWT_SECRETS_LIST[0],
        algorithm=settings.JWT_ALGORITHM,
    )


def create_access_token(user_id: int, role: str) -> str:
    """Create a short-lived access token."""
    return _create_token(
        data={"sub": str(user_id), "role": role, "type": "access"},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(user_id: int) -> str:
    """Create a long-lived refresh token."""
    return _create_token(
        data={"sub": str(user_id), "type": "refresh"},
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )


def _decode_token_with_rotation(token: str, expected_type: str) -> dict[str, Any]:
    """
    Decode and validate a token by attempting each key in settings.JWT_SECRETS_LIST sequentially.
    """
    last_exc = None
    for secret in settings.JWT_SECRETS_LIST:
        try:
            payload = jwt.decode(
                token,
                secret,
                algorithms=[settings.JWT_ALGORITHM],
            )
            if payload.get("type") != expected_type:
                raise UnauthorizedException("Invalid token type")
            return payload
        except JWTError as exc:
            last_exc = exc
            # Try next key in case of signature mismatch, but if expired under primary key
            # it might still be valid or we want to bubble up the last error if all fail.
            continue

    if last_exc and "expired" in str(last_exc).lower():
        raise TokenExpiredException()
    raise UnauthorizedException("Invalid or malformed token")


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode and validate an access token.
    Supports key rotation.
    Raises UnauthorizedException or TokenExpiredException on failure.
    """
    payload = _decode_token_with_rotation(token, "access")
    jti = payload.get("jti")
    if jti and redis_client.get(f"bl_{jti}"):
        raise UnauthorizedException("Token has been revoked")
    return payload


def decode_refresh_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a refresh token.
    Supports key rotation.
    Raises UnauthorizedException or TokenExpiredException on failure.
    """
    return _decode_token_with_rotation(token, "refresh")


def revoke_access_token(jti: str, exp_timestamp: int) -> None:
    """Add a token's JTI to the Redis blacklist until it naturally expires."""
    now = datetime.now(UTC).timestamp()
    ttl = int(exp_timestamp - now)
    if ttl > 0:
        redis_client.setex(f"bl_{jti}", ttl, "revoked")


# ── MFA encryption ────────────────────────────────────────────────────────────

def encrypt_mfa_secret(secret: str) -> str:
    """Encrypt a TOTP secret using Fernet encryption."""
    if not secret:
        return ""
    from cryptography.fernet import Fernet
    f = Fernet(settings.MFA_ENCRYPTION_KEY.encode())
    return f.encrypt(secret.encode()).decode()


def decrypt_mfa_secret(encrypted_secret: str) -> str:
    """Decrypt a TOTP secret using Fernet encryption."""
    if not encrypted_secret:
        return ""
    from cryptography.fernet import Fernet
    try:
        f = Fernet(settings.MFA_ENCRYPTION_KEY.encode())
        return f.decrypt(encrypted_secret.encode()).decode()
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        if settings.is_development:
            logger.warning("Failed to decrypt TOTP secret, falling back to plaintext: %s", e)
            return encrypted_secret
        logger.error("Failed to decrypt TOTP secret for user: %s", e)
        raise
