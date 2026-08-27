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

    # File storage. Local disk (UPLOAD_ROOT) is the default and is what
    # every local dev/test run uses - it's fine for development but does
    # NOT survive a redeploy/restart on most hosts (e.g. Render's
    # filesystem is ephemeral). Setting both SUPABASE_URL and
    # SUPABASE_SERVICE_ROLE_KEY switches app/core/storage.py to Supabase
    # Storage instead, which does persist - see that module's docstring.
    UPLOAD_ROOT: str = "./uploads"
    PUBLIC_UPLOAD_SUBDIR: str = "public"
    PRIVATE_UPLOAD_SUBDIR: str = "private"
    MAX_IMAGE_SIZE_BYTES: int = 5 * 1024 * 1024
    MAX_DOCUMENT_SIZE_BYTES: int = 10 * 1024 * 1024
    SUPABASE_URL: str | None = None
    SUPABASE_SERVICE_ROLE_KEY: str | None = None
    SUPABASE_STORAGE_BUCKET: str = "rockstar-organics-uploads"

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
    # ENVIRONMENT). Defaults to False (safe-by-default, same "explicit
    # opt-in" rule as the notification providers below) - a deployment
    # turns this on deliberately for local/dev use only. get_settings()
    # below refuses to start at all if this is true with ENVIRONMENT=production.
    DEV_EXPOSE_RESET_TOKEN: bool = False

    # Notification providers - disabled unless explicitly configured.
    EMAIL_PROVIDER_ENABLED: bool = False
    SMS_PROVIDER_ENABLED: bool = False
    WHATSAPP_PROVIDER_ENABLED: bool = False

    # Brevo (https://www.brevo.com) transactional email. Both
    # EMAIL_PROVIDER_ENABLED and BREVO_API_KEY must be set for
    # app/core/email.py to actually send. EMAIL_FROM_EMAIL must be an
    # address verified as a sender in the Brevo dashboard (Settings ->
    # Senders) - Brevo rejects sends from an unverified sender outright,
    # there is no sandbox fallback address like some other providers offer.
    BREVO_API_KEY: str | None = None
    EMAIL_FROM_NAME: str = "Rockstar Organics"
    EMAIL_FROM_EMAIL: str | None = None
    PUBLIC_APP_URL: str = "http://localhost:5173"

    # OTP-gated signup (see /api/auth/signup + /api/auth/verify-otp).
    OTP_TTL_MINUTES: int = 10
    OTP_MAX_ATTEMPTS: int = 5
    # When true, the signup OTP code is also returned in the API response,
    # so signup can be completed without a working email provider. Same
    # rule as DEV_EXPOSE_RESET_TOKEN just above - defaults to False.
    DEV_EXPOSE_OTP: bool = False

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


DEFAULT_SECRET_KEY = "dev-secret-key-change-me-before-production"


def _validate_production_settings(s: "Settings") -> None:
    """Fails fast at startup rather than silently running an insecure
    production deployment. Each of these, left at its default/dev value in
    production, is a real account-takeover vector on its own (a forgeable
    session/CSRF/OTP-hash secret, a session cookie sent over plain HTTP, or
    an OTP/reset-token disclosed straight back to whoever requested it) -
    see docs/SECURITY.md for the full detail on each."""
    if s.ENVIRONMENT != "production":
        return
    errors = []
    if s.SECRET_KEY == DEFAULT_SECRET_KEY:
        errors.append("SECRET_KEY is still the default value - set a long random secret.")
    if not s.COOKIE_SECURE:
        errors.append("COOKIE_SECURE must be true in production (cookies must be HTTPS-only).")
    if s.DEV_EXPOSE_OTP:
        errors.append("DEV_EXPOSE_OTP must be false in production - it discloses signup OTP codes in the API response.")
    if s.DEV_EXPOSE_RESET_TOKEN:
        errors.append("DEV_EXPOSE_RESET_TOKEN must be false in production - it discloses password-reset tokens in the API response.")
    if errors:
        raise RuntimeError("Refusing to start with ENVIRONMENT=production and insecure settings:\n- " + "\n- ".join(errors))


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    _validate_production_settings(s)
    return s
