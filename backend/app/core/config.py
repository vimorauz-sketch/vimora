"""Application configuration.

All configuration comes from environment variables (optionally a local .env file in
development). Secrets are never hardcoded. `validate_for_production()` produces a clear
list of missing/unsafe settings so a misconfigured production deployment fails loudly.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Application -------------------------------------------------------------
    APP_ENV: Literal["development", "test", "production"] = "development"
    APP_NAME: str = "VIMORA"
    APP_URL: str = "http://localhost:3000"  # public URL users visit
    FRONTEND_URL: str = "http://localhost:3000"
    API_URL: str = "http://localhost:8000"
    SECRET_KEY: str = ""  # HMAC key for signed URLs / tokens
    SETTINGS_ENCRYPTION_KEY: str = ""  # Fernet key for secrets stored in DB
    CORS_ORIGINS: str = ""  # comma separated; defaults to FRONTEND_URL
    LOG_LEVEL: str = "INFO"
    DEFAULT_LANGUAGE: Literal["uz", "en", "ru"] = "uz"
    DEFAULT_CURRENCY: Literal["UZS", "USD"] = "UZS"
    TIMEZONE: str = "Asia/Tashkent"

    # --- Data stores -------------------------------------------------------------
    DATABASE_URL: str = "postgresql+psycopg://vimora:vimora_dev@127.0.0.1:5432/vimora"
    REDIS_URL: str = "redis://127.0.0.1:6379/0"
    CELERY_BROKER_URL: str = ""
    CELERY_TASK_ALWAYS_EAGER: bool = False

    # --- Sessions / auth -----------------------------------------------------------
    SESSION_COOKIE_NAME: str = "vimora_session"
    CSRF_COOKIE_NAME: str = "vimora_csrf"
    SESSION_TTL_HOURS: int = 24 * 14
    ADMIN_SESSION_TTL_HOURS: int = 12
    SESSION_IDLE_TIMEOUT_HOURS: int = 72
    COOKIE_SECURE: bool | None = None  # None -> secure in production
    COOKIE_DOMAIN: str | None = None
    ADMIN_MFA_REQUIRED: bool | None = None  # None -> required in production
    EMAIL_VERIFICATION_TTL_HOURS: int = 48
    PASSWORD_RESET_TTL_MINUTES: int = 30
    REGISTRATION_ENABLED: bool = True

    # --- Email -----------------------------------------------------------------------
    EMAIL_BACKEND: Literal["smtp", "console", "disabled"] = "smtp"
    EMAIL_HOST: str = ""
    EMAIL_PORT: int = 587
    EMAIL_USERNAME: str = ""
    EMAIL_PASSWORD: str = ""
    EMAIL_FROM: str = ""
    EMAIL_USE_TLS: bool = True
    EMAIL_USE_SSL: bool = False

    # --- Telegram --------------------------------------------------------------------
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_BOT_USERNAME: str = ""
    TELEGRAM_ADMIN_ID: str = ""  # comma separated list of admin Telegram user IDs
    TELEGRAM_NOTIFICATION_CHAT_ID: str = ""
    TELEGRAM_WEBHOOK_SECRET: str = ""
    TELEGRAM_WEBHOOK_URL: str = ""

    # --- AI ----------------------------------------------------------------------------
    AI_PROVIDER: str = ""  # anthropic | openai | openai_compatible
    AI_API_KEY: str = ""
    AI_MODEL: str = ""
    AI_BASE_URL: str = ""
    AI_DAILY_BUDGET: str = "5.00"  # USD
    AI_MAX_TOKENS_PER_CALL: int = 4096
    AI_REQUEST_TIMEOUT_SECONDS: int = 120

    # --- Isolated sandbox for code execution (optional) --------------------------------
    SANDBOX_ENABLED: bool = False
    SANDBOX_DOCKER_HOST: str = ""  # a *separate* docker host dedicated to sandboxes
    SANDBOX_IMAGE: str = "python:3.12-slim"
    SANDBOX_TIMEOUT_SECONDS: int = 60
    SANDBOX_MEMORY: str = "256m"
    SANDBOX_CPUS: str = "0.5"

    # --- Payments ----------------------------------------------------------------------
    CLICK_MERCHANT_ID: str = ""
    CLICK_SERVICE_ID: str = ""
    CLICK_SECRET_KEY: str = ""
    CLICK_MERCHANT_USER_ID: str = ""
    PAYME_MERCHANT_ID: str = ""
    PAYME_SECRET_KEY: str = ""
    PAYME_CHECKOUT_URL: str = "https://checkout.paycom.uz"
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    MANUAL_PAYMENTS_ENABLED: bool = False

    # --- Storage -----------------------------------------------------------------------
    STORAGE_BACKEND: Literal["local", "s3"] = "local"
    LOCAL_STORAGE_PATH: str = "./var/storage"
    S3_ENDPOINT: str = ""
    S3_REGION: str = "us-east-1"
    S3_BUCKET: str = ""
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    MAX_UPLOAD_MB: int = 25
    USER_STORAGE_QUOTA_MB: int = 500
    DOWNLOAD_LINK_TTL_SECONDS: int = 300
    CLAMAV_HOST: str = ""
    CLAMAV_PORT: int = 3310

    # --- Observability -----------------------------------------------------------------
    SENTRY_DSN: str = ""
    HEALTH_DETAILS_TOKEN: str = ""  # required to see detailed health info

    @field_validator("AI_DAILY_BUDGET")
    @classmethod
    def _budget_decimal(cls, v: str) -> str:
        from decimal import Decimal, InvalidOperation

        try:
            if Decimal(v) < 0:
                raise ValueError
        except (InvalidOperation, ValueError) as exc:
            raise ValueError("AI_DAILY_BUDGET must be a non-negative decimal") from exc
        return v

    # ----------------------------------------------------------------------------------
    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def cookie_secure(self) -> bool:
        return self.is_production if self.COOKIE_SECURE is None else self.COOKIE_SECURE

    @property
    def admin_mfa_required(self) -> bool:
        return self.is_production if self.ADMIN_MFA_REQUIRED is None else self.ADMIN_MFA_REQUIRED

    @property
    def cors_origins(self) -> list[str]:
        raw = self.CORS_ORIGINS or self.FRONTEND_URL
        return [o.strip().rstrip("/") for o in raw.split(",") if o.strip()]

    @property
    def broker_url(self) -> str:
        return self.CELERY_BROKER_URL or self.REDIS_URL

    @property
    def telegram_admin_ids(self) -> set[int]:
        out: set[int] = set()
        for part in self.TELEGRAM_ADMIN_ID.split(","):
            part = part.strip()
            if part.lstrip("-").isdigit():
                out.add(int(part))
        return out

    def validate_for_production(self) -> list[str]:
        """Return a list of human readable problems. Empty list == OK."""
        problems: list[str] = []
        if len(self.SECRET_KEY) < 32:
            problems.append("SECRET_KEY must be set to a random value of at least 32 characters")
        if not self.SETTINGS_ENCRYPTION_KEY:
            problems.append("SETTINGS_ENCRYPTION_KEY must be set (python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')")
        if not self.APP_URL.startswith("https://"):
            problems.append("APP_URL must use https:// in production")
        if "vimora_dev" in self.DATABASE_URL:
            problems.append("DATABASE_URL uses the development password")
        if self.EMAIL_BACKEND == "console":
            problems.append("EMAIL_BACKEND=console is not allowed in production")
        if self.EMAIL_BACKEND == "smtp" and not (self.EMAIL_HOST and self.EMAIL_FROM):
            problems.append("EMAIL_HOST and EMAIL_FROM are required for SMTP email (CONFIGURATION REQUIRED)")
        if self.STORAGE_BACKEND == "s3" and not all([self.S3_BUCKET, self.S3_ACCESS_KEY, self.S3_SECRET_KEY]):
            problems.append("S3_BUCKET, S3_ACCESS_KEY and S3_SECRET_KEY are required when STORAGE_BACKEND=s3")
        if self.TELEGRAM_BOT_TOKEN and not self.TELEGRAM_WEBHOOK_SECRET:
            problems.append("TELEGRAM_WEBHOOK_SECRET is required when TELEGRAM_BOT_TOKEN is set")
        if self.COOKIE_SECURE is False:
            problems.append("COOKIE_SECURE must not be disabled in production")
        if self.ADMIN_MFA_REQUIRED is False:
            problems.append("ADMIN_MFA_REQUIRED must not be disabled in production")
        return problems

    def integration_status(self) -> dict[str, bool]:
        """Which optional integrations have credentials configured (no secret values)."""
        return {
            "email": self.EMAIL_BACKEND == "smtp" and bool(self.EMAIL_HOST and self.EMAIL_FROM),
            "telegram": bool(self.TELEGRAM_BOT_TOKEN),
            "ai": bool(self.AI_PROVIDER and self.AI_API_KEY and self.AI_MODEL),
            "click": bool(self.CLICK_MERCHANT_ID and self.CLICK_SERVICE_ID and self.CLICK_SECRET_KEY),
            "payme": bool(self.PAYME_MERCHANT_ID and self.PAYME_SECRET_KEY),
            "stripe": bool(self.STRIPE_SECRET_KEY and self.STRIPE_WEBHOOK_SECRET),
            "s3": self.STORAGE_BACKEND == "s3" and bool(self.S3_BUCKET),
            "sandbox": self.SANDBOX_ENABLED and bool(self.SANDBOX_DOCKER_HOST),
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
