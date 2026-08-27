"""
Double-submit CSRF protection.

Session cookies are already SameSite=Lax, which blocks the cookie being
attached to cross-site POST/PUT/DELETE requests in modern browsers - but
defense in depth is cheap here, and it protects any client that a future
integration might introduce with a looser cookie policy. The pattern:

- On login/register, a random CSRF token is set in a *non-HttpOnly* cookie
  (so frontend JS can read it) alongside the HttpOnly session cookie.
- Every mutating request (POST/PUT/PATCH/DELETE) other than login/register/
  logout (which don't yet have a session to protect, or are ending one)
  must echo that token back in the `X-CSRF-Token` header.
- A cross-site attacker can trigger a cookie-bearing request but cannot
  read the cookie value to put it in the header, so the check fails.
"""
from fastapi import HTTPException, Request

from app.core.config import get_settings
from app.core.security import generate_token

settings = get_settings()

CSRF_COOKIE_NAME = "rso_csrf"
CSRF_HEADER_NAME = "x-csrf-token"

# Paths exempt from the header check: they either establish the session
# (nothing to protect yet) or are safe/idempotent by HTTP method already.
EXEMPT_PATH_PREFIXES = (
    "/api/auth/login",
    "/api/auth/register",
    "/api/auth/logout",
    "/api/auth/forgot-password",
    "/api/auth/reset-password",
    "/api/docs",
    "/api/openapi.json",
)


def new_csrf_token() -> str:
    return generate_token(16)


def csrf_cookie_kwargs() -> dict:
    return dict(
        key=CSRF_COOKIE_NAME,
        httponly=False,  # must be readable by frontend JS to echo in the header
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        path="/",
        max_age=settings.SESSION_MAX_AGE_SECONDS,
    )


async def enforce_csrf(request: Request) -> None:
    if request.method not in ("POST", "PUT", "PATCH", "DELETE"):
        return
    if any(request.url.path.startswith(p) for p in EXEMPT_PATH_PREFIXES):
        return
    # Only relevant to cookie-authenticated (browser) requests. A request
    # with no session cookie at all has nothing for CSRF to ride on.
    if not request.cookies.get(settings.SESSION_COOKIE_NAME):
        return

    cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
    header_token = request.headers.get(CSRF_HEADER_NAME)
    if not cookie_token or not header_token or cookie_token != header_token:
        raise HTTPException(status_code=403, detail="CSRF token missing or invalid.")
