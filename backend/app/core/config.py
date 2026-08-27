"""
Central application configuration, loaded from environment variables.

All settings have safe local-development defaults. Production deployments
MUST override SECRET_KEY, DATABASE_URL and COOKIE_SECURE via environment
variables (see .env.example at the repo root).
"""
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "Rockstar Organics"
    ENVIRONMENT: str = "development"  # development | production | test
    SECRET_KEY: str = "dev-secret-key-change-me-before-production"

    # One-time, idempotent startup bootstrap: create tables (via SQLAlchemy
    # metadata, not Alembic - see app/main.py for why) and required company
    # settings if they don't exist yet. Off by default; a normal deployment
    # applies Alembic migrations explicitly instead (scripts/upgrade_database.py).
    # This exists for hosts where a separate migration step isn't available
    # (e.g. a serverless platform with no persistent shell to run one).
    BOOTSTRAP_SCHEMA: bool = False
    SUPERADMIN_EMAIL: str | None = None
    SUPERADMIN_NAME: str | None = None
    SUPERADMIN_PASSWORD: str | None = None

    # Database. Defaults to a local SQLite file so the project runs with
    # zero external services during development. Production must set
    # DATABASE_URL to a PostgreSQL DSN, e.g.
    # postgresql+psycopg2://user:pass@host:5432/rockstar_organics
    DATABASE_URL: str = "sqlite:///./rockstar_organics.db"

    # Session cookie
    SESSION_COOKIE_NAME: str = "rso_session"
    SESSION_MAX_AGE_SECONDS: int = 60 * 60 * 24 * 7  # 7 days
    COOKIE_SECURE: bool = False  # MUST be True in production (HTTPS only)
    COOKIE_SAMESITE: str = "lax"

    # CORS - frontend dev server origins
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # File storage
    UPLOAD_ROOT: str = "./uploads"
    PUBLIC_UPLOAD_SUBDIR: str = "public"
    PRIVATE_UPLOAD_SUBDIR: str = "private"
    MAX_IMAGE_SIZE_BYTES: int = 5 * 1024 * 1024
    MAX_DOCUMENT_SIZE_BYTES: int = 10 * 1024 * 1024

    # Rate limiting (simple in-memory limiter; see core/rate_limit.py)
    LOGIN_RATE_LIMIT_ATTEMPTS: int = 5
    LOGIN_RATE_LIMIT_WINDOW_SECONDS: int = 300
    PUBLIC_FORM_RATE_LIMIT_ATTEMPTS: int = 10
    PUBLIC_FORM_RATE_LIMIT_WINDOW_SECONDS: int = 600

    # Password reset
    PASSWORD_RESET_TOKEN_TTL_MINUTES: int = 60
    # When true, the password reset token is also returned in the API
    # response, so a reset can be completed without a working email
    # provider. This is its own explicit switch (no longer tied to
    # ENVIRONMENT) - default it to false once real delivery works for every
    # recipient (i.e. once a sending domain is verified with the email
    # provider, removing the sandbox to-your-own-address restriction).
    DEV_EXPOSE_RESET_TOKEN: bool = True

    # Notification providers - disabled unless explicitly configured.
    EMAIL_PROVIDER_ENABLED: bool = False
    SMS_PROVIDER_ENABLED: bool = False
    WHATSAPP_PROVIDER_ENABLED: bool = False

    # Resend (https://resend.com) transactional email. Both EMAIL_PROVIDER_ENABLED
    # and RESEND_API_KEY must be set for app/core/email.py to actually send -
    # see that module's docstring for the sandbox/domain-verification caveat.
    RESEND_API_KEY: str | None = None
    EMAIL_FROM_ADDRESS: str = "Rockstar Organics <onboarding@resend.com>"
    PUBLIC_APP_URL: str = "http://localhost:5173"

    # OTP-gated signup (see /api/auth/signup + /api/auth/verify-otp).
    OTP_TTL_MINUTES: int = 10
    OTP_MAX_ATTEMPTS: int = 5
    # When true, the signup OTP code is also returned in the API response,
    # so signup can be completed without a working email provider. Same
    # rule as DEV_EXPOSE_RESET_TOKEN just above.
    DEV_EXPOSE_OTP: bool = True

    # Dealer availability staleness threshold, in days.
    DEALER_AVAILABILITY_STALE_DAYS: int = 14

    # Shared rate limiting across processes/instances. Unset -> falls back
    # to the in-memory limiter (fine for a single dev process, NOT safe for
    # a multi-worker/multi-instance production deployment). See
    # app/core/rate_limit.py.
    REDIS_URL: str | None = None

    # Error tracking (Sentry). Unset -> Sentry is never initialized, matching
    # the same "explicit opt-in, no silent fake state" rule used for the
    # email/SMS/WhatsApp providers.
    SENTRY_DSN: str | None = None
    SENTRY_TRACES_SAMPLE_RATE: float = 0.1

    # Prometheus metrics. The /metrics endpoint is only mounted when this is
    # true, so it isn't accidentally exposed on a deployment that has no
    # scraper/auth in front of it.
    METRICS_ENABLED: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
