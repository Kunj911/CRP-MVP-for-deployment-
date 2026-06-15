"""
core/config.py

Centralized settings management using Pydantic Settings.
Loads configuration from environment variables and environment files.
"""

import base64
import logging
import logging.config
from functools import lru_cache
from typing import Literal, Optional
from urllib.parse import quote_plus
from cryptography.fernet import Fernet
from pydantic import computed_field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_config_logger = logging.getLogger("livetrace.config")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App settings ──────────────────────────────────────────────────────────
    APP_NAME: str = "Client Relationship Portal"
    APP_ENV: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = True

    @field_validator("DEBUG", mode="before")
    @classmethod
    def _parse_debug(cls, value):
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"release", "prod", "production", "false", "0", "no", "off"}:
                return False
            if normalized in {"debug", "dev", "development", "true", "1", "yes", "on"}:
                return True
        return value

    # ── Database ──────────────────────────────────────────────────────────────
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_NAME: str = "live_trace_dashboard"
    DB_USER: str = "root"
    DB_PASSWORD: str = "2104"

    # ── Redis ─────────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_REQUIRED: bool = False  # Set True in staging/production to fail startup without Redis

    @computed_field
    @property
    def DATABASE_URL(self) -> str:
        user = quote_plus(self.DB_USER)
        password = quote_plus(self.DB_PASSWORD)
        return (
            f"mysql+pymysql://{user}:{password}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
        )

    # ── Auth settings ─────────────────────────────────────────────────────────
    JWT_SECRET_KEY: str = "change-this-secret"
    JWT_SECRET_KEYS: str = ""  # Comma-separated list of secrets for rotation
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    MFA_ENCRYPTION_KEY: str = ""  # 32-byte Fernet key for encrypting totp_secret
    MFA_REQUIRED_ROLES: str = "SUPER_ADMIN,ADMIN"

    @computed_field
    @property
    def JWT_SECRETS_LIST(self) -> list[str]:
        if not self.JWT_SECRET_KEYS:
            return [self.JWT_SECRET_KEY]
        return [k.strip() for k in self.JWT_SECRET_KEYS.split(",") if k.strip()]

    # ── Malware Scanning (ClamAV) ─────────────────────────────────────────────
    CLAMAV_ENABLED: bool = False
    CLAMAV_HOST: str = "localhost"
    CLAMAV_PORT: int = 3310
    CLAMAV_FAIL_CLOSED: bool = False

    # ── Observability ─────────────────────────────────────────────────────────
    SENTRY_DSN: str = ""
    PROMETHEUS_METRICS_ENABLED: bool = False
    METRICS_PASSWORD: str = "metrics-secure-password-123!"

    # ── Seed API (one-time dataset import) ──────────────────────────────────────
    SEED_API_KEY: str = ""
    SEED_DEFAULT_PASSWORD: str = "Temp@123"

    # ── Async Workers (Celery) ────────────────────────────────────────────────
    CELERY_ENABLED: bool = False

    # ── Storage settings ──────────────────────────────────────────────────────
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

    @computed_field
    @property
    def MAX_PHOTO_SIZE_BYTES(self) -> int:
        return self.MAX_PHOTO_SIZE_MB * 1024 * 1024

    @computed_field
    @property
    def MAX_DOCUMENT_SIZE_BYTES(self) -> int:
        return self.MAX_DOCUMENT_SIZE_MB * 1024 * 1024

    # ── CORS & CSRF ───────────────────────────────────────────────────────────
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:3000,http://localhost"

    @computed_field
    @property
    def CORS_ORIGINS(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    # ── Redirect Allowed Domains ──────────────────────────────────────────────
    ALLOWED_REDIRECT_DOMAINS: str = "localhost,127.0.0.1,db,redis,clamav"

    @computed_field
    @property
    def REDIRECT_DOMAINS(self) -> list[str]:
        return [d.strip().lower() for d in self.ALLOWED_REDIRECT_DOMAINS.split(",") if d.strip()]

    # ── SMTP / Email Configuration ────────────────────────────────────────
    SMTP_ENABLED: bool = True
    SMTP_HOST: str = "smtp-relay.brevo.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    SMTP_FROM_NAME: str = ""
    SMTP_USE_TLS: bool = True

    # ── Legacy Email & WhatsApp Notifications (Compatibility) ──────────────────
    EMAIL_ENABLED: bool = True
    EMAIL_PROVIDER: Literal["resend", "smtp", "sendgrid"] = "smtp"
    EMAIL_FROM: str = ""
    EMAIL_FROM_NAME: str = ""
    RESEND_API_KEY: str = ""
    RESEND_API_URL: str = "https://api.resend.com/emails"
    FRONTEND_APP_URL: str = "https://live-trace-fittree.up.railway.app"
    BACKEND_URL: str = "https://backend-production-3b9b2.up.railway.app"

    SMTP_USER: str = ""
    SMTP_TLS: bool = True

    WHATSAPP_API_URL: str = ""
    WHATSAPP_TOKEN: str = ""

    # ── Future features data parameters ──────────────────────────────────────
    DATA_RETENTION_DAYS: int = 365
    STORAGE_ENCRYPTION: bool = False

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def is_staging(self) -> bool:
        return self.APP_ENV == "staging"

    @property
    def is_deployed(self) -> bool:
        """True for any non-development environment (staging, production)."""
        return self.APP_ENV != "development"

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"

    @model_validator(mode="after")
    def _enforce_security_policies(self) -> "Settings":
        """
        Enforce deployment security configurations.
        """
        _WEAK_SECRETS = {"change-this-secret", "secret", "password", ""}

        primary_key = self.JWT_SECRETS_LIST[0]
        if self.APP_ENV != "development":
            if primary_key in _WEAK_SECRETS or len(primary_key) < 32:
                raise ValueError(
                    f"SECURITY BLOCK: JWT secret key is too weak for '{self.APP_ENV}' environment. Use a random string >= 32 characters."
                )
        else:
            if primary_key in _WEAK_SECRETS or len(primary_key) < 32:
                _config_logger.warning(
                    "Primary JWT secret key is weak. Permitted in development mode only."
                )

        if self.MFA_ENCRYPTION_KEY:
            try:
                key_bytes = base64.urlsafe_b64decode(self.MFA_ENCRYPTION_KEY.encode())
                if len(key_bytes) != 32:
                    raise ValueError("Key must decode to 32 bytes")
            except Exception as e:
                if self.APP_ENV != "development":
                    raise ValueError(f"SECURITY BLOCK: MFA_ENCRYPTION_KEY must be a valid 32-byte Fernet key. {e}")
                else:
                    _config_logger.warning("MFA_ENCRYPTION_KEY is invalid. Re-generating...")
                    object.__setattr__(self, "MFA_ENCRYPTION_KEY", Fernet.generate_key().decode())
        else:
            if self.APP_ENV != "development":
                raise ValueError("SECURITY BLOCK: MFA_ENCRYPTION_KEY is required in production.")
            else:
                object.__setattr__(self, "MFA_ENCRYPTION_KEY", Fernet.generate_key().decode())

        if self.APP_ENV in ("production", "staging") and self.DEBUG:
            _config_logger.warning("Force-disabling DEBUG mode in %s environment.", self.APP_ENV)
            object.__setattr__(self, "DEBUG", False)

        if self.APP_ENV in ("production", "staging"):
            for origin in self.CORS_ORIGINS:
                if origin == "*":
                    raise ValueError(f"SECURITY BLOCK: CORS wildcard '*' is not allowed in {self.APP_ENV}.")

            _DEFAULTS_TO_BLOCK = {
                "METRICS_PASSWORD": ("metrics-secure-password-123!", self.METRICS_PASSWORD),
                "SEED_DEFAULT_PASSWORD": ("Temp@123", self.SEED_DEFAULT_PASSWORD),
            }
            for field_name, (bad_value, actual_value) in _DEFAULTS_TO_BLOCK.items():
                if actual_value == bad_value:
                    raise ValueError(
                        f"SECURITY BLOCK: {field_name} is set to the insecure default '{bad_value}' "
                        f"in '{self.APP_ENV}' environment. Set a strong unique value via environment variable."
                    )

            _DEFAULTS_TO_WARN = {
                "DB_PASSWORD": ("2104", self.DB_PASSWORD),
            }
            for field_name, (bad_value, actual_value) in _DEFAULTS_TO_WARN.items():
                if actual_value == bad_value:
                    _config_logger.warning(
                        "WARNING: %s is set to the default value '%s' in '%s' environment. "
                        "This is strongly discouraged for production.",
                        field_name, bad_value, self.APP_ENV,
                    )

        # Bind new SMTP variables to legacy counterparts for backward compatibility
        if self.SMTP_USERNAME and not self.SMTP_USER:
            object.__setattr__(self, "SMTP_USER", self.SMTP_USERNAME)
        elif self.SMTP_USER and not self.SMTP_USERNAME:
            object.__setattr__(self, "SMTP_USERNAME", self.SMTP_USER)

        if self.SMTP_USE_TLS is not None:
            object.__setattr__(self, "SMTP_TLS", self.SMTP_USE_TLS)

        if not self.EMAIL_FROM:
            from_email = self.SMTP_FROM_EMAIL or "noreply@example.com"
            from_name = self.SMTP_FROM_NAME or "Client Relationship Portal"
            object.__setattr__(self, "EMAIL_FROM", f"{from_name} <{from_email}>")

        if not self.EMAIL_FROM_NAME:
            object.__setattr__(self, "EMAIL_FROM_NAME", self.SMTP_FROM_NAME or "Client Relationship Portal")

        if self.EMAIL_PROVIDER.lower() == "smtp":
            object.__setattr__(self, "EMAIL_ENABLED", self.SMTP_ENABLED)

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
