# Test Report

Generated from an actual run against this build (see command output below;
not a projection).

## Backend — pytest

Command: `cd backend && source venv/bin/activate && pytest -v`

Result: **49 passed, 0 failed**, run against a temporary SQLite database
created fresh per test session.

| File | Tests | Covers |
|---|---|---|
| `test_auth.py` | 7 | Registration/login, generic invalid-login error, suspended account blocked, role cannot be client-supplied, unauthorised dashboard access blocked, full password reset flow (including token reuse rejection), login rate limiting. |
| `test_products.py` | 4 | Empty catalogue by default, full draft→published→unpublished→archived lifecycle with visibility checks at each step, SKU/slug uniqueness, publish-time field validation. |
| `test_dealers.py` | 4 | Application submission → approval → automatic dealer account creation with forced password change, duplicate application detection, consent requirement, directory opt-in/suspension visibility. |
| `test_cases_and_matching.py` | 4 | Farmer case isolation (farmer A cannot see farmer B's case), transparent district/mandal matching, dealer opt-out excluded from matches, private staff notes hidden from farmers. |
| `test_reviews_and_security.py` | 7 | Reviews pending by default and hidden until moderated, approved reviews counted into rating, rejected reviews excluded, reviews blocked on unpublished products, security headers present, role restriction on staff-only endpoints, dealer profile ownership restriction. |
| `test_zzz_content_and_tasks.py` | 6 | Announcement draft→published→archived visibility, knowledge article publish blocked without approval step, follow-up task overdue flag and completion, validated product image upload + public retrieval, rejection of a disguised file (wrong file signature for declared type), case attachment private access control (owner can access, other farmer gets 403). |
| `test_security_hardening.py` | 10 | CSRF token required for mutating requests once a session exists, CSRF not required for anonymous requests, change-password requires the current password, password change invalidates other sessions, farmer/dealer account suspension via the accounts endpoints (including removal from the dealer directory), review comment length is capped, enquiry submission requires explicit consent, password maximum length is enforced, blank optional email on an enquiry is accepted rather than rejected (regression test for a bug the Playwright E2E suite caught - see below). |
| `test_real_world_content.py` | 7 | Email sending is a real no-op (not a lie) when the provider is disabled; OTP signup issues a code, rejects the wrong code, and cannot be replayed; signup rejects a duplicate email; a distributor application approval creates a working, loggable-in account; a company document cannot be published before verification and becomes publicly downloadable only after both; an agriculture photo cannot be approved/published without usage rights verified, and unverified fields render "Information pending verification." rather than being invented. |

## Frontend — Vitest

Command: `cd frontend && npm run test`

Result: **2 passed, 0 failed** (component-level: `StatusBadge`,
`EmptyState`). This is a starting unit-test set, not full coverage — see
Known Limitations for Playwright browser-flow tests, which are not yet
included.

## Frontend — build and typecheck

- `npx tsc -b` — passes with no errors (re-verified after the change-password,
  account management, enquiry-queue, Sentry/error-boundary, and E2E-tooling
  additions).
- `npm run build` — succeeds; production bundle ~352 KB JS / 8.6 KB CSS
  (gzip: ~101 KB / ~2.4 KB).

## Frontend/backend — end-to-end (Playwright)

Command: `cd frontend && npm run e2e` (backend running separately, built
frontend served via `vite preview` — see `.github/workflows/ci.yml`'s
`e2e-tests` job for the exact sequence).

Result: **9 passed, 0 failed** — home page load, product catalogue render
with no console error, a real Contact-form enquiry submission through to
a returned reference number, farmer registration through to the farmer
dashboard, an invalid login showing a generic error (not a stack trace),
the 404 page for an unknown route, a distributor application submission
through to a reference number, the full OTP signup flow (send code ->
real 6-digit dev code appears in the UI -> verify -> redirected to the
farmer dashboard), and the certificates/gallery pages rendering with no
console error.

This suite is what actually found a real bug during the security pass: the
public Contact form's optional email field submits `""` when left blank,
and the backend's `EmailStr | None` schema rejected `""` outright ("not a
valid email address"), which no existing unit or integration test caught
because none of them exercised the real browser form. Fixed with a
`field_validator` that treats a blank/whitespace-only email the same as
"not provided" (`backend/app/schemas/schemas.py`), covered by a new
regression test (`test_enquiry_with_blank_optional_email_is_accepted` in
`test_security_hardening.py`). All 6 tests from that pass plus the 3 new
ones added for the real-world content pass (distributor apply, OTP
signup, certificates/gallery) pass together: 9/9.

## Manual verification performed

- Fresh SQLite database created, Alembic migration applied cleanly
  (`alembic upgrade head`), required company-setting keys seeded with
  `scripts/seed_required_data.py` (0 business records seeded, as required).
- `scripts/create_superadmin.py` run interactively; created a Super
  Administrator account successfully.
- `scripts/seed_demo_accounts.py` run against a live backend: created all
  four spec demo accounts, then a real end-to-end curl-based flow
  confirmed: a distributor application submitted publicly, approved by
  the demo Super Admin, and the resulting temporary-password login
  actually worked (role `distributor`, `must_change_password: true`); a
  real OTP signup issued a 6-digit dev code and `verify-otp` created a
  usable, logged-in farmer account.
- A live Resend API key was created via the Resend account connected
  during this session and a real send was attempted against Resend's
  production API - see `docs/SECURITY.md`'s "Email delivery" section for
  the exact result (blocked by the account's lack of a verified sending
  domain, not a code defect) and `docs/KNOWN_LIMITATIONS.md` for what
  this does and doesn't mean for "real email."
- Backend started with `uvicorn app.main:app`; `/api/v1/health` and
  `/api/v1/ready` both returned 200 with `{"status": "ok"/"ready", ...}`.
- Full request/response smoke test via `TestClient`: registration, login,
  session cookie round-trip, `/api/v1/auth/me` all verified.

## Known gaps

- The Playwright suite is a smoke suite (6 flows), not exhaustive coverage
  of every page/role combination — extend `frontend/e2e/` as new
  higher-risk flows are added (dealer application review, field visit
  scheduling, staff moderation actions).
- Frontend component test coverage is intentionally minimal (2 tests) — the pytest
  suite carries the majority of behavioral verification since business
  logic and permission enforcement live server-side, per the "backend
  validation is authoritative" principle in the spec.
- Migration upgrade-from-previous-schema tests are not applicable yet
  (this is the initial schema; there is no prior version to upgrade from).
