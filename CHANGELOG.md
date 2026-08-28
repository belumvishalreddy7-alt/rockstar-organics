# Changelog

## 1.6.0 — Production deployment readiness (Render + Vercel + Supabase + Brevo)

- Added `render.yaml` documenting the backend's actual Render service
  configuration (no secrets - every sensitive var is `sync: false`),
  including a corrected start command that runs `alembic upgrade head`
  before serving traffic, matching the Docker path's existing behavior.
- README, `docs/STAFF_GUIDE.md`: replaced stale Resend/test-count
  references with the real Brevo/Supabase setup; added a full "Deployment"
  section documenting the actual Vercel+Render+Supabase+Brevo topology,
  a Troubleshooting section, and certificate/agriculture-photo/rating-
  moderation staff workflows that were previously undocumented. Removed
  leftover UTF-16 garbage bytes at the end of README.md.
- `.github/workflows/ci.yml`: added a header comment clarifying that the
  AWS ECS deploy jobs are an inactive alternative path, not what this
  project actually deploys through.
- Closed a dangling-reference gap in `/tasks/{id}/assign/{assignee_id}`
  and `/enquiries/{id}/assign/{staff_id}`: both now 404 if the assignee/
  staff id doesn't correspond to a real user (matches the same fix
  already applied to case assignment).
- Verified (did not change): no hardcoded secrets anywhere in the repo;
  `SUPABASE_SERVICE_ROLE_KEY`/`BREVO_API_KEY` never reach the frontend
  bundle; Alembic's migration chain applies cleanly to PostgreSQL via an
  offline dry run; every frontend API call maps to a real backend route.

## 1.4.0 — Real-world content pass

- New Distributor role and portal: application -> verification -> approval
  -> activation (mirrors the dealer workflow), public `/distributors`
  apply page, staff `Distributor applications` review, a distributor
  dashboard (profile, territory, declared stock).
- OTP-gated signup: `POST /api/auth/signup` -> `POST /api/auth/verify-otp`.
  No account exists until the emailed code is verified. New `/signup`
  frontend flow (2-step: details, then code). The original `/register`
  flow is kept as-is.
- Company certificates & official documents: Uploaded -> Under Review ->
  Verified -> Published, enforced server-side (publishing before
  verification is rejected by the API). Public `/certificates` page,
  staff `Certificates & documents` CRUD.
- Agriculture photo gallery: usage rights must be verified before a photo
  can be approved or published (enforced server-side). Location, crop,
  date, and photographer/source render "Information pending
  verification." when unset rather than being invented. Public
  `/gallery` page, staff `Agriculture gallery` CRUD.
- Real (not mocked) transactional email via Resend
  (`backend/app/core/email.py`): OTP codes, password resets, welcome
  emails, and dealer/distributor approval credentials. Verified live
  against the real Resend API during this pass - see
  `docs/SECURITY.md`/`docs/KNOWN_LIMITATIONS.md` for the exact result
  (a real API key works; delivery is currently blocked by the connected
  Resend account having no verified sending domain, not by the code).
- Public navigation and footer updated to match the spec's list (Home,
  About, Products, Dealers, Distributors, Contact, Login) plus role-login
  and legal footer sections; About/Contact pages now show "Information
  pending verification." for any unverified company field instead of
  placeholder marketing copy.
- Development demo accounts (`scripts/seed_demo_accounts.py`) for all
  four roles named in the spec; refuses to run in production.
- Backend suite grew to 49 tests (`test_real_world_content.py`, 7 new
  tests); frontend E2E suite grew to 9 Playwright tests (distributor
  apply, OTP signup, certificates/gallery rendering). All passing.

## 1.3.0 — Production infrastructure pass

- CI/CD: `.github/workflows/ci.yml` — backend pytest, frontend typecheck/
  vitest/build, and a new Playwright E2E smoke suite gate image builds;
  production deploy is a separate, approval-gated job.
- End-to-end tests: `frontend/e2e/smoke.spec.ts` (Playwright), covering
  home/catalogue rendering, a real Contact-form enquiry submission,
  farmer registration through to the dashboard, invalid-login error
  handling, and the 404 page. Running this suite found and fixed a real
  bug: the Contact form's optional email field sent `""`, which the
  backend's `EmailStr | None` schema rejected outright; fixed with a
  blank-string-to-`None` validator plus a regression test.
- Error tracking: Sentry wired on backend (`SENTRY_DSN`) and frontend
  (`VITE_SENTRY_DSN` + a top-level React error boundary), inert unless a
  DSN is configured.
- Monitoring: `/metrics` (Prometheus, `METRICS_ENABLED`), a Prometheus +
  Grafana Docker Compose profile with a starter dashboard, and alert
  rules for error rate/latency/uptime/readiness.
- Shared rate limiting: `app/core/rate_limit.py` gained a Redis-backed
  implementation (`REDIS_URL`) so limits hold across multiple backend
  workers/instances, with a visible fallback (log warning + failing
  `/api/ready`) instead of silently under-limiting.
- Hosting/scaling: a Terraform module for AWS (ECS Fargate, RDS,
  ElastiCache, S3, ALB, CPU autoscaling) and a parallel Kubernetes
  manifest set (Deployment, HPA, Ingress, backup CronJob).
- Backups: `ops/backups/backup_db.sh` / `restore_db.sh` (pg_dump to S3).
- `/api/ready` now reports Redis connectivity (when configured) alongside
  the existing database check.
- Backend suite grew to 42 tests (the blank-email regression test); all
  green. Frontend `tsc -b`, `vitest run`, `npm run build`, and the new
  `npm run e2e` all pass.

## 1.2.0 — Security and connectivity hardening pass

- Real double-submit CSRF protection (`app/core/csrf.py`, `rso_csrf`
  cookie + `X-CSRF-Token` header) replacing the previous `SameSite=Lax`-
  only mitigation, enforced globally for mutating requests once a session
  exists.
- Session invalidation on password change: session tokens now embed a
  `password_changed_at` stamp and are rejected once that stamp goes stale,
  so a password change (self-service or staff-forced) kills every other
  outstanding session for that account.
- New self-service `POST /api/auth/change-password` endpoint and
  `/change-password` page; a `ForcedPasswordChangeGate` redirects any
  signed-in user with `must_change_password=true` there before they can
  reach anything else.
- New farmer/dealer account suspension endpoints and UI
  (`app/routers/accounts.py`, `Staff → Accounts`) — previously only staff
  accounts had a status lifecycle.
- Public Contact page rebuilt into a real, working enquiry submission form
  wired to the existing backend Enquiry API, plus a staff `Enquiries`
  queue page to triage submissions — previously the backend had no
  connected frontend entry point.
- Review rate-limiting re-keyed to client IP instead of the spoofable
  reviewer-name field.
- Enquiry consent now requires an explicit `true` rather than defaulting
  to given.
- Request body size cap (413) ahead of all handlers; explicit 256-char
  password maximum.
- Consolidated three raw `fetch()`-based upload call sites into a shared
  `uploadFile()` API-client helper so they carry CSRF headers correctly.
- New `backend/tests/test_security_hardening.py` (9 tests); full backend
  suite now 41/41 passing. Frontend `tsc -b`, `vitest run`, `npm run
  build` re-verified clean.

## 1.1.0 — Content and connectivity gap-fill

- Announcements: full draft → in review → published → archived lifecycle,
  staff CRUD UI, public listing/detail pages.
- Knowledge Centre: full draft → in review → approved → published →
  archived/rejected lifecycle with a mandatory approval step, staff CRUD
  UI, public listing/detail pages.
- Real, validated media upload pipeline (`app/core/uploads.py`):
  extension/MIME/magic-byte validation, random storage filenames, public/
  private storage separation. Wired into product images, farmer case
  attachments, and dealer application documents.
- Follow-up task management UI (`Staff → Follow-up tasks`).
- Backend suite grew to 32 tests covering all of the above.

## 1.0.0 — Initial build

- Full auth system: registration, login, logout, password reset, rate
  limiting, session cookies, role enforcement.
- Product lifecycle (draft → published) with publish-time validation.
- Dealer application → approval → dealer account creation workflow.
- Dealer profile, service areas, product availability, public directory.
- Farmer support cases with transparent dealer matching, assignment,
  status workflow, public/private timeline.
- Field visit request/schedule/complete workflow with conflict checking
  and automatic follow-up task creation.
- Product review submission and moderation; ratings from approved reviews
  only.
- Enquiries, notifications (in-app; external channels explicitly
  disabled-by-default), company settings, audit logging, CSV report
  export, live dashboard metrics.
- React/TypeScript frontend: public site, farmer portal, dealer portal,
  staff dashboard, custom design system, accessible forms/empty states/
  status badges.
- Backend pytest suite (26 tests), frontend Vitest suite, Docker Compose
  deployment (PostgreSQL + backend + nginx-served frontend), Windows
  setup/start scripts, full documentation set.
