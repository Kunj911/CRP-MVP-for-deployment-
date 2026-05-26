"""
config/settings.py

Single source of truth for all environment configuration.
Loaded once at startup via get_settings() and cached.
"""

import logging
import warnings
from functools import lru_cache
from typing import Literal, Optional

from pydantic import computed_field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_settings_logger = logging.getLogger("livetrace.settings")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ───────────────────────────────────────────────────────────────────
    APP_NAME: str = "Live-Trace"
    APP_ENV: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = False

    # ── Security ──────────────────────────────────────────────────────────────
    # AUTH-004: MFA readiness — roles that will require MFA once implemented
    MFA_REQUIRED_ROLES: str = "SUPER_ADMIN,ADMIN"

    # ── Database ──────────────────────────────────────────────────────────────
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_NAME: str = "livetrace"
    DB_USER: str = "root"
    DB_PASSWORD: str = ""
    
    # ── Redis ─────────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    @computed_field  # type: ignore[misc]
    @property
    def DATABASE_URL(self) -> str:
        from urllib.parse import quote_plus
        encoded_password = quote_plus(self.DB_PASSWORD)
        return (
            f"mysql+pymysql://{self.DB_USER}:{encoded_password}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            "?charset=utf8mb4"
        )

    # ── Auth ──────────────────────────────────────────────────────────────────
    JWT_SECRET_KEY: str = "change-this-secret"
    JWT_SECRET_KEYS: str = ""  # Comma-separated list of secrets for rotation
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    MFA_ENCRYPTION_KEY: str = ""  # 32-byte Fernet key for encrypting totp_secret

    @computed_field  # type: ignore[misc]
    @property
    def JWT_SECRETS_LIST(self) -> list[str]:
        if not self.JWT_SECRET_KEYS:
            return [self.JWT_SECRET_KEY]
        return [k.strip() for k in self.JWT_SECRET_KEYS.split(",") if k.strip()]

    # ── Malware Scanning ──────────────────────────────────────────────────────
    CLAMAV_ENABLED: bool = False
    CLAMAV_HOST: str = "localhost"
    CLAMAV_PORT: int = 3310
    CLAMAV_FAIL_CLOSED: bool = False

    # ── Observability ─────────────────────────────────────────────────────────
    SENTRY_DSN: str = ""
    PROMETHEUS_METRICS_ENABLED: bool = False

    # ── Async Workers / Celery ────────────────────────────────────────────────
    CELERY_ENABLED: bool = False

    # ── Data retention (DATA-003 — future implementation) ─────────────────────
    DATA_RETENTION_DAYS: int = 365

    # ── Storage encryption (DATA-001 — future implementation) ─────────────────
    STORAGE_ENCRYPTION: bool = False

    # ── Storage ───────────────────────────────────────────────────────────────
    STORAGE_BACKEND: Literal["local", "s3", "cloudinary"] = "local"
    LOCAL_UPLOAD_DIR: str = "./uploads"

    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_S3_BUCKET: str = ""
    AWS_S3_REGION: str = "ap-south-1"

    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""

    # ── Upload limits ─────────────────────────────────────────────────────────
    MAX_PHOTO_SIZE_MB: int = 10
    MAX_DOCUMENT_SIZE_MB: int = 25

    @computed_field  # type: ignore[misc]
    @property
    def MAX_PHOTO_SIZE_BYTES(self) -> int:
        return self.MAX_PHOTO_SIZE_MB * 1024 * 1024

    @computed_field  # type: ignore[misc]
    @property
    def MAX_DOCUMENT_SIZE_BYTES(self) -> int:
        return self.MAX_DOCUMENT_SIZE_MB * 1024 * 1024

    # ── CORS ──────────────────────────────────────────────────────────────────
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    @computed_field  # type: ignore[misc]
    @property
    def CORS_ORIGINS(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    # ── Email ─────────────────────────────────────────────────────────────────
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM_NAME: str = "Live-Trace"

    # ── WhatsApp ──────────────────────────────────────────────────────────────
    WHATSAPP_API_URL: str = ""
    WHATSAPP_TOKEN: str = ""

    # ── Helpers ───────────────────────────────────────────────────────────────
    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"

    # ── Security validators ──────────────────────────────────────────────────

    @model_validator(mode="after")
    def _enforce_security_policies(self) -> "Settings":
        """
        Post-init security checks:
          AUTH-001: Block weak JWT secrets outside development.
          AUTH-002: Force DEBUG off in production.
          CONFIG-003: Reject wildcard / http:// CORS origins in production.
        """
        _WEAK_SECRETS = {"change-this-secret", "secret", "password", ""}

        # Validate and ensure primary key strength (AUTH-001)
        primary_key = self.JWT_SECRETS_LIST[0]
        if self.APP_ENV != "development":
            if primary_key in _WEAK_SECRETS or len(primary_key) < 32:
                raise ValueError(
                    "SECURITY BLOCK (AUTH-001): JWT primary secret key is too weak for "
                    f"'{self.APP_ENV}' environment. Use a random string ≥ 32 characters. "
                    "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(48))\""
                )
        else:
            if primary_key in _WEAK_SECRETS or len(primary_key) < 32:
                _settings_logger.warning(
                    "AUTH-001: Primary JWT secret key is weak. Acceptable in development only."
                )

        # Validate MFA_ENCRYPTION_KEY is a valid base64-encoded 32-byte key
        if self.MFA_ENCRYPTION_KEY:
            try:
                import base64
                key_bytes = base64.urlsafe_b64decode(self.MFA_ENCRYPTION_KEY.encode())
                if len(key_bytes) != 32:
                    raise ValueError("Key must decode to 32 bytes")
            except Exception as e:
                if self.APP_ENV != "development":
                    raise ValueError(
                        f"SECURITY BLOCK: MFA_ENCRYPTION_KEY must be a valid 32-byte Fernet key. {e}"
                    )
                else:
                    _settings_logger.warning(
                        "MFA_ENCRYPTION_KEY is not a valid 32-byte Fernet key. Re-generating..."
                    )
                    from cryptography.fernet import Fernet
                    object.__setattr__(self, "MFA_ENCRYPTION_KEY", Fernet.generate_key().decode())
        else:
            # Generate a key if it is not provided (dev environment only)
            if self.APP_ENV != "development":
                raise ValueError("SECURITY BLOCK: MFA_ENCRYPTION_KEY is required in production.")
            else:
                from cryptography.fernet import Fernet
                object.__setattr__(self, "MFA_ENCRYPTION_KEY", Fernet.generate_key().decode())

        # AUTH-002 — Force DEBUG off in production
        if self.APP_ENV == "production" and self.DEBUG:
            _settings_logger.warning(
                "AUTH-002: DEBUG was True in production — forcing to False."
            )
            object.__setattr__(self, "DEBUG", False)

        # CONFIG-003 — CORS origin hardening in production
        if self.APP_ENV == "production":
            for origin in self.CORS_ORIGINS:
                if origin.strip() == "*":
                    raise ValueError(
                        "SECURITY BLOCK (CONFIG-003): Wildcard '*' CORS origin "
                        "is not allowed in production."
                    )
                if origin.strip().startswith("http://"):
                    _settings_logger.warning(
                        "CONFIG-003: HTTP origin '%s' detected in production CORS. "
                        "Consider using HTTPS only.",
                        origin,
                    )

        return self


@lru_cache
def get_settings() -> Settings:
    """Return cached Settings instance. Import this — never instantiate Settings directly."""
    return Settings()
