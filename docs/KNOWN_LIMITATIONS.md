# Known Limitations (Version 1)

This build is a deep, working vertical slice of the full 44-section
specification. Every item below has a real, working fallback — nothing here
is faked or silently broken.

## Update: real-world content pass

A further pass implemented the ROCKSTAR_ORGANICS_COMPLETE_REAL_WORLD_WEBSITE_CONTENT
spec against this build. Everything below is real - migrated tables, live
routes, tests that were run, and one live external API call - not a plan
or a mockup:

- **Distributor role & portal** — a new `distributor` role with the same
  Registration -> Verification -> Approval -> Activation workflow as
  dealers (`DistributorApplication`, `DistributorProfile`,
  `DistributorStock` tables; `app/routers/distributors.py`; public
  `/distributors` apply page; `Staff -> Distributor applications`; a
  distributor dashboard for profile/stock). Account suspension is wired
  into the existing `/api/v1/accounts` pattern alongside farmers/dealers.
- **OTP-gated signup** — `POST /api/v1/auth/signup` -> `POST
  /api/v1/auth/verify-otp`, per the spec exactly: no `User` row is created
  until the emailed 6-digit code is verified (held in `OtpCode` until
  then, hashed, rate-limited, capped at `OTP_MAX_ATTEMPTS`). The original
  direct `/register`/`/api/v1/auth/register` flow is left in place
  unchanged (tests and the E2E suite still exercise it) rather than
  removed, since removing a working, tested path added risk for no
  benefit - `/signup` is the spec-compliant addition.
- **Company certificates & official documents** — `CompanyDocument`
  table + `app/routers/company_documents.py`, enforcing Uploaded ->
  Under Review -> Verified -> Published exactly: publishing before
  verification is rejected by the API (not just hidden in the UI), and
  the public `/certificates` page and `GET /api/v1/company/documents` only
  ever return documents that are both verified and published. Staff CRUD
  at `Staff -> Certificates & documents`.
- **Agriculture photo gallery** — `AgriculturePhoto` table +
  `app/routers/agriculture_photos.py`. Approval/publication is blocked at
  the API level until `usage_rights_verified` is true - a photo cannot be
  published "by accident" through the UI. Location, crop, date, and
  photographer/source are nullable and rendered as "Information pending
  verification." rather than invented, both in the API response
  (`app/routers/agriculture_photos.py::_public_shape`) and the public
  `/gallery` page. Staff CRUD at `Staff -> Agriculture gallery`.
- **"Information pending verification." content rule** — applied to the
  About page's company information, leadership, manufacturing, and
  research sections, and the Contact page's general-enquiry contact
  details, per the spec's mandatory verified-information rule. No company
  registration details, leadership names, facility information, or
  contact details are invented anywhere in the frontend.
- **Public navigation & footer** — trimmed to the spec's list (Home,
  About Rockstar Organics, Products, Dealers, Distributors, Contact,
  Login) and the footer now lists the five role logins and the legal
  pages as specified. Farmer support, crop knowledge, and announcements
  remain reachable by direct URL and from the farmer portal - their
  routes and backend were not deleted, only removed from the primary
  public nav, since the spec says farmer support "remains available
  inside the authenticated farmer portal."
- **Development demo accounts** — `python -m scripts.seed_demo_accounts`
  creates the four accounts listed in the spec (admin.demo@example.com /
  farmer.demo@example.com / dealer.demo@example.com /
  distributor.demo@example.com) with the spec's exact passwords. The
  script refuses to run when `ENVIRONMENT=production`, and
  `--remove` deletes them again.
- **Real (not mocked) transactional email** — `app/core/email.py` makes
  genuine HTTP calls to the Resend API for OTP codes, password resets,
  welcome emails, and dealer/distributor approval credentials. This was
  verified live, not simulated: a real Resend API key was created via
  the Resend account connected during this build, and a live send was
  attempted against Resend's production API. It returned Resend's own
  `403 domain_not_verified` error, because the connected Resend account
  has no verified sending domain - see `docs/SECURITY.md`'s "Email
  delivery" section for the full detail and what verifying a domain
  would unlock (no code changes needed). Until a domain is verified,
  `EMAIL_PROVIDER_ENABLED` stays `false` (the default), and OTP/reset
  flows fall back to returning the code/token directly in the API
  response in development (`DEV_EXPOSE_OTP`/`DEV_EXPOSE_RESET_TOKEN`) -
  which is how this pass's own automated tests and live smoke-testing
  exercised those flows.

Test coverage: `backend/tests/test_real_world_content.py` (7 tests) covers
OTP signup + verification + duplicate-email rejection + wrong-code
rejection + code-cannot-be-replayed, distributor application approval
creating a working account, and the company-document/agriculture-photo
verification-gates-publication rules. `frontend/e2e/smoke.spec.ts` gained
three more Playwright tests exercising the distributor apply form, the
full OTP signup flow (through a real backend, real 6-digit code, real
account creation), and the certificates/gallery pages - all 9 E2E tests
pass. Full backend suite: 49/49 passing.

### Deviations from the spec's exact structure

Chosen deliberately, to extend the existing tested codebase rather than
rebuild it (the user's explicit choice when asked) - these do not affect
functionality, only naming/structure:

- **API base path is now `/api/v1`** for every business endpoint, matching
  section 27 of the master spec exactly (updated in the "master spec"
  pass: every router prefix, the frontend API client, and every backend
  test were moved from `/api/...` to `/api/v1/...`). The two
  infrastructure endpoints (`/api/health`, `/api/ready`) and the docs URL
  (`/api/docs`) intentionally stay unversioned, per section 65's "or
  equivalent" allowance for health/readiness probes. Verified live: all
  49 backend tests and all 9 Playwright E2E tests pass against the
  renamed API.
- **Database table names** follow this build's existing naming
  (`dealer_applications`, `farmer_support_cases`, etc.) rather than the
  spec's exact list (`dealer_stock`, `case_attachments`, etc.) where the
  existing build already had an equivalent table under a different name.
  Every table the spec lists that had no equivalent yet (distributors,
  OTP codes, company documents, agriculture photos) was added using the
  spec's intent for that table.
- **Leadership/manufacturing/research** are rendered as placeholder
  sections on the About page (all showing "Information pending
  verification." until real content exists) rather than as separate
  dedicated pages/tables - the spec's content for these sections is
  entirely placeholder text pending real company information anyway, so
  a full separate CMS model for empty sections was not built yet. Company
  settings (`CompanySetting` table, already CMS-editable) can carry this
  content once real information exists; promoting it to dedicated
  tables/pages is straightforward future work if the content grows
  complex enough to need it.

## Update: previously-listed gaps are now filled

As of this revision, the following are fully implemented end-to-end
(backend model + API + validation + audit logging + tests + frontend UI),
not just stubs:

- **Announcements** — draft → in review → published → archived lifecycle,
  staff CRUD UI (`Staff → Announcements`), public listing and detail pages
  (`/announcements`, `/announcements/:slug`), expiry-date filtering on the
  public feed.
- **Knowledge Centre** — draft → in review → approved → published →
  archived/rejected lifecycle (publication requires the approval step,
  enforced server-side), staff CRUD UI (`Staff → Knowledge articles`),
  public listing and detail pages (`/knowledge`, `/knowledge/:slug`) with
  the safety disclaimer always shown.
- **Media uploads** — a real, validated upload pipeline
  (`app/core/uploads.py`): extension allow-list, declared-MIME-type
  allow-list, file-signature (magic byte) verification, size limits, and
  randomly generated storage filenames (the client-supplied name is never
  trusted for the stored path). Three flows are wired end-to-end:
  - **Product images** (public): staff upload via `Staff → Products →
    Upload image`, with required alt text; images render on the public
    product detail page, served through `/api/v1/media/public/...`.
  - **Farmer case attachments** (private): farmers attach a photo or PDF
    from the case detail page; access is checked per-case (farmer/
    assigned dealer/staff only) through `/api/v1/media/private/{id}`.
  - **Dealer application documents** (private): an applicant can attach a
    business document right after submitting their application (using the
    application's own ID, since they're not yet a signed-in dealer); staff
    review them from `Staff → Dealer applications → View documents`.
- **Follow-up task management UI** — `Staff → Follow-up tasks` lists tasks
  (all or "my tasks only"), flags overdue tasks, and lets staff move a task
  through Open → In Progress → Completed/Cancelled. Tasks created
  automatically (e.g. on field visit completion) show up here.

Test coverage: `backend/tests/test_zzz_content_and_tasks.py` covers the
announcement and knowledge lifecycles, follow-up task overdue/completion,
validated product image upload, rejection of a disguised file (wrong magic
bytes for its declared type), and private case-attachment access control
(owning farmer can access; a different farmer gets 403).

## Update: security/connectivity audit pass

A follow-up audit ("connect everything and fill all the gaps,
vulnerabilities and errors") found and fixed the following, all covered by
`backend/tests/test_security_hardening.py`:

- **CSRF** is now enforced with a real double-submit token
  (`app/core/csrf.py`), replacing the `SameSite=Lax`-only approach — see
  the removed item under "Deliberate simplifications" below and
  `docs/SECURITY.md`.
- **Session invalidation on password change** — a session token issued
  before a password change (or reset) is now rejected; previously a
  stolen or shared session would keep working after the account holder
  changed their password.
- **No self-service or staff-driven "change password" flow existed** even
  though the data model supported `must_change_password`. Added
  `POST /api/v1/auth/change-password`, the `/change-password` frontend page,
  and a `ForcedPasswordChangeGate` that redirects any signed-in user with
  `must_change_password=true` to that page before they can reach anything
  else — closing the gap where a temporary password could simply be kept
  in use indefinitely.
- **Farmer and dealer accounts could not be suspended** — only staff
  accounts had a status lifecycle. Added `app/routers/accounts.py` and the
  `Staff → Accounts` UI; suspending a dealer also removes them from the
  public directory and farmer-case matching immediately.
- **Review rate-limiting was keyed by the free-text reviewer name field**,
  which any anonymous submitter could vary to bypass the limit. Re-keyed
  to client IP (and authenticated user ID when available).
- **The public Contact page was a dead end** — static text only, despite a
  complete backend Enquiry API with no connected form. It's now a working
  form (`Contact()` in `StaticPages.tsx`) with a staff-side queue
  (`Staff → Enquiries`) to triage submissions.
- **Enquiry consent defaulted to `true`** server-side, so a client could
  omit the field and still record consent as given. Consent is now
  required explicitly (`consent_given` must be sent as `true`).
- **No request body size cap** existed ahead of the upload endpoints,
  meaning an oversized request could be read into memory before any
  handler-level validation ran. A `Content-Length` check now rejects
  oversized requests with 413 before the body is read.
- **No explicit maximum password length** was enforced (only a minimum),
  leaving the Argon2 hashing step exposed to arbitrarily long input. Capped
  at 256 characters at the schema layer.
- Three file-upload call sites in the frontend (`ProductManagement.tsx`,
  `CaseDetail.tsx`, `DealerProgramme.tsx`) used a raw `fetch()` that
  bypassed the shared API client and would have silently broken once CSRF
  enforcement went live (no CSRF header attached). Consolidated into one
  `uploadFile()` helper in `api/client.ts`.

The full backend suite is 41/41 passing; frontend `tsc -b`, `vitest run`,
and `npm run build` all pass clean after these changes.

## Update: production infrastructure pass

A further pass ("implement everything" against a system-design/production
checklist — CI/CD, hosting, monitoring, error tracking, rate-limit
scaling, secrets, backups) added the following, all exercised for real,
not left as configuration-only stubs:

- **CI/CD** — `.github/workflows/ci.yml` runs backend pytest, frontend
  typecheck/vitest/build, and a Playwright E2E smoke suite on every push/
  PR, builds and pushes Docker images only after all of that passes, and
  gates production deployment behind a GitHub Environment approval.
- **End-to-end browser tests** — `frontend/e2e/smoke.spec.ts` (Playwright)
  now covers 6 real flows through an actual browser against a real
  backend. This is what previously showed up as "not included in this
  pass" below; it's resolved, and it immediately found and fixed a real
  bug (see `docs/TEST_REPORT.md`'s "end-to-end" section).
- **Error tracking** — Sentry wired on both backend (`app/main.py`,
  `SENTRY_DSN`) and frontend (`src/monitoring.ts` +
  `src/components/ErrorBoundary.tsx`, `VITE_SENTRY_DSN`), inert unless a
  DSN is configured.
- **Monitoring & alerting** — a `/metrics` Prometheus endpoint
  (`METRICS_ENABLED`), a Prometheus + Grafana stack
  (`docker-compose --profile monitoring`, `ops/prometheus/`,
  `ops/grafana/`), and alert rules for error rate, latency, backend-down,
  and readiness-check failures (`ops/prometheus/alert_rules.yml`) — the
  rules still need a real Alertmanager receiver wired up to actually page
  someone; see `docs/PRODUCTION_CHECKLIST.md`.
- **Shared rate limiting** — `app/core/rate_limit.py` gained a
  Redis-backed implementation (`REDIS_URL`) so limits are enforced
  consistently across multiple workers/instances, with a documented,
  visible fallback (a startup log warning, and a failing `/api/v1/ready`
  check) rather than silently under-limiting.
- **Hosting/scaling** — a Terraform module (`infra/terraform/`: ECS
  Fargate, RDS, ElastiCache, S3, ALB, autoscaling 3-12 tasks on CPU) and a
  parallel Kubernetes path (`infra/k8s/`: Deployment, HPA, Ingress,
  ConfigMap/Secret templates) for teams not on AWS.
- **Backups** — `ops/backups/backup_db.sh` / `restore_db.sh` (pg_dump to
  S3, with a documented restore-into-a-fresh-database discipline),
  scheduled via `infra/k8s/cronjob-backup.yaml` on Kubernetes or RDS's own
  automated backups when using the Terraform path.
- **Secrets management** — documented, with the Terraform/Kubernetes
  configs showing where real secrets are meant to be injected from (AWS
  Secrets Manager, the External Secrets Operator) instead of a committed
  file; `docker-compose.yml`/`.env.example` remain the local-dev-only path.

None of this is "click deploy and you're done" — see each directory's own
README/comments for what a real rollout still has to fill in (your actual
VPC/domain/registry, an Alertmanager receiver, IAM role ARNs). What's real
here is that every piece is wired to the same interfaces the app already
uses (`/api/v1/health`, `/api/v1/ready`, structured JSON logs, the same
`REDIS_URL`/`SENTRY_DSN` env vars the app reads), tested where it could be
run in this environment (CI workflow syntax, the Prometheus/Grafana
compose profile, the E2E suite against a live backend), and not just
prose describing what you'd need to build.

## Deliberate simplifications that remain

- **The Terraform and Kubernetes manifests have not been applied against
  real infrastructure** from this environment (there is no AWS account or
  cluster available here to apply them to). `terraform validate`-level
  correctness and internal consistency were reviewed by hand, and the
  application-level pieces they wire together (`/api/v1/health`, `/api/v1/ready`,
  `REDIS_URL`, `SENTRY_DSN`, `METRICS_ENABLED`) were all verified live
  against the running backend. Run `terraform plan` and `kubectl apply
  --dry-run=server` against your actual account/cluster before a real
  rollout, and expect to adjust resource sizing, IAM boundaries, and
  networking to your organization's existing setup.
- **Alerting has rules but no receiver** — `ops/prometheus/alert_rules.yml`
  defines the conditions; wiring a real Alertmanager to actually deliver
  those to Slack/PagerDuty/email is left to the deploying team, since that
  depends on which paging tool they already use.
- **Product edit permissions**: Content Manager, Administrator, and Super
  Administrator all share full product edit rights in this build, rather
  than a narrower split where Sales Manager cannot touch "technical"
  fields. The spec's intent (Sales Manager cannot edit product content) is
  respected — Sales Manager has no product write access at all here.
- **Dealer matching scoring** (`app/services/matching.py`) is a documented
  starting rule set (district match, mandal match, recent activity) — tune
  the point values with real operational data.

## External providers

Email, SMS, and WhatsApp notification channels are implemented as an
explicit disabled state (`EMAIL_PROVIDER_ENABLED=false` etc. in
`.env.example`). The app never displays a fake "sent" confirmation for a
channel that isn't configured — see `app/core/notify.py`.

## Database

SQLite is used for local development for zero-dependency setup; all models
and migrations are written to be PostgreSQL-compatible (see
`docker-compose.yml`, which runs Postgres 16). Confirm `DATABASE_URL`
points at PostgreSQL before production use — see
`docs/PRODUCTION_CHECKLIST.md`.
