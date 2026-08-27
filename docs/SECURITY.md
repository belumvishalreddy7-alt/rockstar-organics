# Security Notes

- **Passwords:** Argon2id via `argon2-cffi` (`app/core/security.py`).
  Strength policy enforced server-side (10+ chars, mixed case, digit,
  256-char maximum enforced both at the Pydantic schema layer and the
  strength-check function).
- **Sessions:** signed, HTTP-only cookies (`itsdangerous`), `SameSite=Lax`,
  `Secure` in production, 7-day expiry. Each session token embeds a
  `password_changed_at` stamp (`app/core/deps.py`); on password change the
  server re-stamps the user and rejects any session token carrying a stale
  stamp, so changing (or having staff reset) a password invalidates every
  other outstanding session for that account immediately, not just the
  browser that made the change.
- **CSRF:** enforced with a double-submit cookie pattern
  (`app/core/csrf.py`). A non-HttpOnly `rso_csrf` cookie is issued
  alongside every session cookie; every mutating request (POST/PUT/PATCH/
  DELETE) that carries a session cookie must also echo that value in the
  `X-CSRF-Token` header, or the request is rejected with 403 before it
  reaches any route handler. Requests with no session cookie (anonymous
  dealer applications, enquiries, public reviews, login/register/logout/
  password-reset itself) are exempt, since CSRF only matters once a
  session exists. This replaces the previous `SameSite=Lax`-only mitigation
  documented as a known limitation in earlier passes — that limitation is
  now resolved.
- **Request size limits:** the same middleware that enforces CSRF rejects
  any request whose `Content-Length` exceeds the largest configured upload
  size plus 1&nbsp;MB of headroom, returning 413 before the body is read.
- **Rate limiting:** in-memory sliding window (`app/core/rate_limit.py`) on
  login, registration, password reset requests, dealer applications,
  enquiries, and reviews. Review rate-limiting is keyed by client IP (and
  authenticated user ID, when present) rather than by the free-text
  reviewer name field, which was previously spoofable to bypass the limit.
  Swap the limiter for a Redis-backed implementation behind the same
  interface for a multi-process production deployment — the current
  in-memory version does not share state across worker processes.
- **Account suspension:** staff with the `super_admin`/`admin` roles can
  suspend or disable farmer accounts, and dealer-facing managers can
  suspend or disable dealer accounts, via `/api/accounts/{farmers|dealers}/
  {id}/status/{status}` (`app/routers/accounts.py`). Suspending a dealer
  account also flips `DealerProfile.suspended`, immediately removing that
  dealer from the public directory and from farmer-case matching.
- **SQL injection:** all queries go through SQLAlchemy's ORM/query builder;
  no raw string-interpolated SQL exists in the codebase.
- **XSS:** React escapes all rendered content by default; no
  `dangerouslySetInnerHTML` is used anywhere in this build.
- **Security headers:** `X-Content-Type-Options`, `X-Frame-Options`,
  `Referrer-Policy`, `Content-Security-Policy`, and (production only)
  `Strict-Transport-Security` are set on every response
  (`app/main.py::security_headers_and_logging`).
- **Error handling:** unhandled exceptions return a generic message plus a
  reference ID for support correlation; no stack trace is ever returned to
  the client. Server-side, the full traceback is logged with that same
  reference ID.
- **Audit logging:** every privileged action writes an `AuditLog` row with
  actor, action, entity, timestamp, and a safe (non-secret) summary. See
  `app/core/audit.py`. Passwords, tokens, and full documents are never
  logged.
- **File uploads:** `app/core/uploads.py` validates every upload against
  an extension allow-list, a declared-MIME-type allow-list, and a
  file-signature (magic byte) check, and stores the file under a randomly
  generated filename — the user-supplied filename is never trusted for
  storage. Public assets (product images) and private documents (dealer
  application documents, case attachments) are kept in separate storage
  roots with separate access rules, wired through `app/routers/media.py`.
- **Dependency hygiene:** pin versions in `requirements.txt` /
  `package.json`; run `pip list --outdated` / `npm outdated` periodically
  and update deliberately, testing after each bump.
- **Error tracking:** Sentry is wired on both backend (`app/main.py`,
  `SENTRY_DSN`) and frontend (`src/monitoring.ts`, `src/components/
  ErrorBoundary.tsx`, `VITE_SENTRY_DSN`), but stays completely inert
  unless a DSN is configured — no client is created, nothing is captured,
  matching the same opt-in pattern used for the notification providers.
  `send_default_pii=False` on the backend client so request bodies/user
  PII are never sent to Sentry by default.
- **Metrics endpoint:** `/metrics` (Prometheus format) is only mounted
  when `METRICS_ENABLED=true`; it carries no application-level
  authentication, so it must only ever be reachable from a private
  scraper network, not the public internet — see
  `docs/PRODUCTION_CHECKLIST.md`.
- **Shared rate limiting:** `app/core/rate_limit.py` now supports a
  Redis-backed sliding-window limiter (`REDIS_URL`) so limits are
  enforced consistently across every worker/instance, not just within one
  process. `/api/ready` reports Redis connectivity explicitly and fails
  readiness if `REDIS_URL` is configured but unreachable, so a
  misconfiguration is visible in health checks rather than silently
  degrading to per-process (and therefore weaker) limits.
- **Secrets management:** see `docs/PRODUCTION_CHECKLIST.md`'s "Secrets
  management" section — `SECRET_KEY`, database credentials, and the
  Sentry DSN/auth token are never committed; the Terraform and Kubernetes
  configs under `infra/` show where to wire them to a real secrets store.

## Email delivery (Resend)

`app/core/email.py` is a real HTTP integration with the Resend API
(`https://api.resend.com/emails`), not a mock: with `EMAIL_PROVIDER_ENABLED=true`
and a real `RESEND_API_KEY` set, signup OTP codes, password-reset links,
welcome emails, and dealer/distributor approval credentials are sent
through an actual API call, and the response's real success/failure is
what the caller sees (`EmailResult.sent`) - the app never claims an email
was sent when the API call failed.

**What was verified during this build**, live, against the real Resend
API (not simulated): a Resend API key was created for this project via the
Resend account connected to this session, and a live send was attempted
against it. Resend rejected the send with its own `403 domain_not_verified`
error, because the connected account has no verified sending domain yet -
Resend restricts every account to the shared `onboarding@resend.com`
sender or a verified domain's addresses, and this account has neither
verified. This is a Resend account configuration state, not a code
defect: `app/core/email.py`'s request/response handling, error surfacing,
and the OTP/password-reset/approval flows that call it are all real and
were exercised end-to-end in tests and in a live backend (see
`docs/TEST_REPORT.md`) - the only missing piece is a verified domain on
the Resend side. Once a domain is verified at
https://resend.com/domains and `EMAIL_FROM_ADDRESS` is set to an address
on it, mail will start delivering with no code changes.

Until a domain is verified, `EMAIL_PROVIDER_ENABLED` should stay `false`
(the default) so the app doesn't pointlessly attempt sends that Resend
will reject - the OTP/reset flows fall back to returning the code/token
directly in the API response when `DEV_EXPOSE_OTP`/`DEV_EXPOSE_RESET_TOKEN`
are true, which is how this build's own tests and manual verification
exercised those flows without live email.
