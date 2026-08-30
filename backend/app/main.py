"""
Rockstar Organics API entrypoint.

Wires together security middleware, routers, central error handling, and
health/readiness endpoints. Run with:
    uvicorn app.main:app --reload
"""
import logging
import time
import uuid

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.config import get_settings
from app.core.csrf import enforce_csrf
from app.core.database import SessionLocal, engine
from app.routers import (
    accounts,
    agriculture_photos,
    announcements,
    auth,
    categories,
    certifications,
    company_documents,
    company_page_content,
    dealers,
    distributors,
    enquiries,
    cases,
    farmers,
    knowledge,
    leadership,
    manufacturing,
    media,
    notifications,
    products,
    reports,
    research,
    reviews,
    settings_router,
    staff,
    staff_applications,
    sustainability,
    tasks,
    visits,
)

settings = get_settings()

logging.basicConfig(
    level=logging.INFO,
    format='{"time": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}',
)
logger = logging.getLogger("rockstar_organics")

# Error tracking: only initialized when SENTRY_DSN is set, so a deployment
# that hasn't configured Sentry gets no behavior change (no client, no
# background threads, no silent no-op "sent" state) - same opt-in pattern
# used for the email/SMS/WhatsApp notification providers.
if settings.SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.starlette import StarletteIntegration

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        integrations=[StarletteIntegration(), FastApiIntegration()],
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        send_default_pii=False,
    )
    logger.info('{"message": "Sentry error tracking initialized"}')

app = FastAPI(
    title="Rockstar Organics API",
    version="1.0.0",
    docs_url="/api/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url=None,
)

if settings.BOOTSTRAP_SCHEMA:
    # See Settings.BOOTSTRAP_SCHEMA's docstring: opt-in, idempotent, only
    # for hosts with no separate migration step. Runs once per cold start;
    # never raises, so a transient DB hiccup doesn't take the whole app
    # down - /api/ready already reports real database connectivity.
    try:
        from app.core.database import Base, SessionLocal, engine
        from app.core.permissions import ROLE_SUPER_ADMIN
        from app.core.security import hash_password, password_strength_errors
        from app.models.models import CompanySetting, User
        from app.routers.settings_router import REQUIRED_KEYS

        Base.metadata.create_all(bind=engine)
        with SessionLocal() as db:
            for key in REQUIRED_KEYS:
                if not db.get(CompanySetting, key):
                    db.add(CompanySetting(key=key, value=None))
            db.commit()

            if settings.SUPERADMIN_EMAIL and settings.SUPERADMIN_NAME and settings.SUPERADMIN_PASSWORD:
                email = settings.SUPERADMIN_EMAIL.lower()
                if not db.query(User).filter(User.email == email).first():
                    errors = password_strength_errors(settings.SUPERADMIN_PASSWORD)
                    if errors:
                        logger.warning('{"message": "SUPERADMIN_PASSWORD does not meet strength requirements, skipping bootstrap"}')
                    else:
                        db.add(User(
                            email=email, password_hash=hash_password(settings.SUPERADMIN_PASSWORD),
                            role=ROLE_SUPER_ADMIN, full_name=settings.SUPERADMIN_NAME,
                            status="active", must_change_password=False, email_verified=True,
                        ))
                        db.commit()
                        logger.info('{"message": "Bootstrap: super administrator account ensured"}')
        logger.info('{"message": "Bootstrap: schema and required settings ensured"}')
    except Exception:
        logger.exception('{"message": "Bootstrap failed"}')

# Prometheus metrics at /metrics - opt-in via METRICS_ENABLED so it's never
# exposed on a deployment that hasn't decided to scrape/protect it.
if settings.METRICS_ENABLED:
    from prometheus_fastapi_instrumentator import Instrumentator

    Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

# Requests larger than this are rejected before any parsing happens, so a
# malicious or buggy client can't force the server to buffer an enormous
# body (a cheap memory-exhaustion DoS lever). Generous enough for a file
# upload up to the document size limit plus form overhead.
MAX_REQUEST_BODY_BYTES = max(settings.MAX_DOCUMENT_SIZE_BYTES, settings.MAX_IMAGE_SIZE_BYTES) + (1024 * 1024)


@app.middleware("http")
async def security_headers_and_logging(request: Request, call_next):
    request_id = uuid.uuid4().hex[:12]

    content_length = request.headers.get("content-length")
    if content_length and content_length.isdigit() and int(content_length) > MAX_REQUEST_BODY_BYTES:
        return JSONResponse(status_code=413, content={"detail": "Request body too large."})

    try:
        await enforce_csrf(request)
    except HTTPException as exc:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    start = time.time()
    try:
        response = await call_next(request)
    except Exception as exc:
        logger.exception('{"request_id": "%s", "path": "%s"}', request_id, request.url.path)
        if settings.SENTRY_DSN:
            import sentry_sdk

            sentry_sdk.set_tag("request_id", request_id)
            sentry_sdk.capture_exception(exc)
        return JSONResponse(
            status_code=500,
            content={"detail": "An unexpected error occurred.", "reference_id": request_id},
        )
    duration_ms = round((time.time() - start) * 1000, 2)
    logger.info(
        '{"request_id": "%s", "method": "%s", "path": "%s", "status": %s, "duration_ms": %s}',
        request_id, request.method, request.url.path, response.status_code, duration_ms,
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    response.headers["X-Request-ID"] = request_id
    if settings.ENVIRONMENT == "production":
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    return response


# Registered *after* security_headers_and_logging so it becomes the
# outermost middleware layer (Starlette wraps in reverse registration
# order - the most recently added middleware runs first on the way in and
# last on the way out). That matters here: security_headers_and_logging
# returns some responses (CSRF rejection, oversized body) directly without
# calling call_next(), which would otherwise skip CORSMiddleware entirely -
# leaving those error responses without CORS headers and making a
# legitimate cross-origin rejection look like a generic CORS failure to
# the browser instead of a readable error.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # The CSRF token is echoed in this response header (see
    # app/core/csrf.py::expose_csrf_token) so a cross-origin frontend can
    # capture it - it cannot read the rso_csrf cookie itself, since cookies
    # are scoped to the domain that set them. Browsers hide all response
    # headers from cross-origin JS by default unless explicitly exposed.
    expose_headers=["X-CSRF-Token"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = [f"{'.'.join(str(p) for p in e['loc'][1:])}: {e['msg']}" for e in exc.errors()]
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content={"detail": "; ".join(errors)})


app.include_router(auth.router)
app.include_router(products.router)
app.include_router(categories.router)
app.include_router(dealers.router)
app.include_router(farmers.router)
app.include_router(cases.router)
app.include_router(visits.router)
app.include_router(enquiries.router)
app.include_router(reviews.router)
app.include_router(notifications.router)
app.include_router(settings_router.router)
app.include_router(reports.router)
app.include_router(staff.router)
app.include_router(announcements.router)
app.include_router(knowledge.router)
app.include_router(tasks.router)
app.include_router(media.router)
app.include_router(accounts.router)
app.include_router(distributors.router)
app.include_router(company_documents.router)
app.include_router(agriculture_photos.router)
app.include_router(company_page_content.router)
app.include_router(leadership.router)
app.include_router(manufacturing.router)
app.include_router(research.facilities_router)
app.include_router(research.areas_router)
app.include_router(certifications.router)
app.include_router(sustainability.router)
app.include_router(staff_applications.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.APP_NAME}


@app.get("/api/ready")
def ready():
    checks: dict[str, str] = {}
    healthy = True
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        checks["database"] = "connected"
    except Exception as exc:
        checks["database"] = f"error: {exc}"
        healthy = False

    if settings.REDIS_URL:
        try:
            from app.core.rate_limit import rate_limiter, RedisRateLimiter

            if isinstance(rate_limiter, RedisRateLimiter):
                rate_limiter._redis.ping()
                checks["redis"] = "connected"
            else:
                checks["redis"] = "configured but limiter fell back to in-memory at startup"
                healthy = False
        except Exception as exc:
            checks["redis"] = f"error: {exc}"
            healthy = False

    status_code = 200 if healthy else 503
    return JSONResponse(
        status_code=status_code,
        content={"status": "ready" if healthy else "not_ready", **checks},
    )
