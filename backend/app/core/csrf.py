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
from fastapi import HTTPException, Request, Response

from app.core.config import get_settings
from app.core.security import generate_token

settings = get_settings()

CSRF_COOKIE_NAME = "rso_csrf"
CSRF_HEADER_NAME = "x-csrf-token"

# Paths exempt from the header check: they either establish the session
# (nothing to protect yet) or are safe/idempotent by HTTP method already.
EXEMPT_PATH_PREFIXES = (
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/signup",
    "/api/v1/auth/verify-otp",
    "/api/v1/auth/logout",
    "/api/v1/auth/forgot-password",
    "/api/v1/auth/reset-password",
    "/api/docs",
    "/api/openapi.json",
)


def new_csrf_token() -> str:
    return generate_token(16)


def expose_csrf_token(response: Response, token: str) -> None:
    """Makes the CSRF token readable by frontend JS via the response body/
    header in addition to the cookie. A same-origin deployment (Docker/
    nginx) can read the `rso_csrf` cookie directly via document.cookie, but
    a standalone cross-origin deployment (frontend on Vercel, API on a
    different host) cannot: cookies are scoped to the domain that set them,
    so JS running on the frontend's origin has no access to a cookie set by
    the API's origin. Echoing the same token in a response header - which
    CORSMiddleware is configured to expose - lets the frontend capture it
    regardless of deployment topology."""
    response.headers[CSRF_HEADER_NAME] = token


def mirror_csrf_cookie_header(request: Request, response: Response) -> None:
    """For requests that don't reissue a new CSRF token (e.g. GET /auth/me
    on page load), echo back whatever token the browser already sent via
    the cookie so a cross-origin frontend - which cannot read that cookie
    itself - can (re)capture it after a refresh or direct navigation."""
    token = request.cookies.get(CSRF_COOKIE_NAME)
    if token:
        response.headers[CSRF_HEADER_NAME] = token


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
