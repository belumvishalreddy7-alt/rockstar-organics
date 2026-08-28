# Rockstar Organics

A database-backed platform for an agricultural products company operating in
Hyderabad, Ranga Reddy, and the surrounding Telangana region: a public
website, farmer portal, dealer portal, and staff dashboards, connected end to
end to a real database.

## What is in this build

This is a **deep vertical slice**, not the full 44-section specification.
Every feature listed below is real: it saves to and reads from the database,
enforces role permissions on the server, and is covered by automated tests.
It deliberately does not attempt every module in the original specification
(see `docs/KNOWN_LIMITATIONS.md` for the explicit list of what's out of
scope in this build and why).

Included and working end-to-end:

- Authentication: registration (farmers), login/logout, Argon2 password
  hashing, password reset with expiring tokens, login rate limiting,
  generic error messages, session cookies, account status enforcement.
- Role-based authorization enforced server-side for: Super Administrator,
  Administrator, Content Manager, Sales Manager, Field Officer, Dealer,
  Farmer, and public/anonymous users.
- Product lifecycle: draft → in review → approved → published →
  unpublished/archived, with publish-time validation, SKU/slug uniqueness,
  and public visibility rules.
- Dealer applications: public submission, duplicate detection, staff
  review/approve/reject, automatic dealer account creation on approval with
  a forced password change.
- Dealer portal: profile, directory opt-in, farmer-case opt-in, product
  availability declarations, service areas.
- Farmer support cases: submission, a transparent (explained, scored)
  dealer-matching algorithm, staff assignment, a timeline with public vs.
  private (staff/dealer-only) messages, status workflow.
- Field visits: request, conflict-checked scheduling, completion with
  automatic follow-up task creation.
- Product reviews: pending by default, staff moderation, ratings computed
  only from approved reviews.
- Announcements and Knowledge Centre articles: full draft→review→
  publish lifecycles (knowledge requires an approval step before
  publication), staff CRUD UI, public listing/detail pages.
- Media uploads: a real, validated pipeline (extension + MIME + file-
  signature checks, random storage filenames) for public product images,
  private farmer case attachments, and private dealer application
  documents — each access-controlled appropriately.
- Enquiries: a real public enquiry form (`/contact`) wired to the backend
  API, with a staff triage queue (`Staff → Enquiries`).
- Farmer/dealer account suspension (`Staff → Accounts`), self-service and
  forced password-change flow (`/change-password`, gated automatically
  for any account with `must_change_password` set).
- Follow-up tasks (with a staff task board and overdue flagging), in-app
  notifications, company settings, audit logging, CSV report export,
  dashboard metrics computed from the database (never hardcoded).
- Double-submit CSRF protection, session invalidation on password change,
  security headers, IP-based rate limiting, request body size limits,
  structured logging, central error handling with reference IDs.
- Distributor role and portal: public application (`/distributors`), staff
  review/approve/reject, automatic distributor account creation on
  approval, and a distributor dashboard (profile, territory, declared
  stock) — mirrors the dealer workflow end to end.
- OTP-gated signup (`/signup`): no account is created until a real, emailed
  6-digit code is verified (`POST /api/v1/auth/signup` → `POST
  /api/v1/auth/verify-otp`); the original direct `/register` flow still works
  unchanged.
- Company certificates & official documents: Uploaded → Under Review →
  Verified → Published, enforced server-side (publishing before
  verification is rejected by the API, not just hidden in the UI); public
  `/certificates` page, staff CRUD.
- Agriculture photo gallery: usage rights must be verified before a photo
  can be approved or published (enforced server-side); unverified fields
  (location, crop, date, photographer/source) render "Information pending
  verification." instead of being invented; public `/gallery` page, staff
  CRUD.
- Real (not mocked) transactional email via Brevo (`app/core/email.py`):
  OTP codes, password resets, welcome emails, and dealer/distributor
  approval credentials. Brevo was chosen specifically because this
  deployment has no custom domain — a single verified sender address
  (Brevo dashboard → Settings → Senders) is enough to send to arbitrary
  recipients, with no domain-verification requirement. See
  `docs/SECURITY.md` for the current delivery status.
- Development demo accounts for all roles (`backend/scripts/
  seed_demo_accounts.py`); refuses to run when `ENVIRONMENT=production`.

## Technology stack

- **Backend:** Python 3.11+, FastAPI, SQLAlchemy 2, Alembic, Pydantic v2,
  Argon2 password hashing, itsdangerous session cookies.
- **Frontend:** React 19, TypeScript, Vite, React Router, TanStack Query,
  a custom CSS design system (no component-library default styling).
- **Database:** PostgreSQL in production (Supabase); SQLite is supported
  for local development using the same SQLAlchemy models and Alembic
  migrations.
- **File storage:** local disk for development; Supabase Storage in
  production (`app/core/storage.py`) — a pluggable backend, so uploads
  survive redeploys instead of living on ephemeral container disk.
- **Email:** Brevo (`app/core/email.py`) — see "Email delivery" above.
- **Testing:** Pytest (backend, 58 tests), Vitest (frontend component
  tests), Playwright (end-to-end browser smoke tests, 10 tests).
- **Ops:** GitHub Actions CI (test suite only — see "Deployment" below
  for how this project actually ships), Sentry error tracking, Prometheus
  + Grafana monitoring, Redis-backed rate limiting. `infra/terraform/`
  (AWS) and `infra/k8s/` are alternative deployment paths this project
  supports but does not currently use in production — see
  `docs/PRODUCTION_CHECKLIST.md`.

## Folder structure

```
rockstar-organics/
  backend/
    app/
      core/        # config, database, security, permissions, rate limiting, deps
      models/       # SQLAlchemy models (one file, clearly sectioned)
      schemas/       # Pydantic request/response schemas
      routers/      # FastAPI routers, one per domain
      services/       # business logic that doesn't belong in a router (matching)
      main.py       # app entrypoint, middleware, security headers
    alembic/        # migrations
    scripts/        # doctor.py, create_superadmin.py, upgrade_database.py, seed_required_data.py
    tests/        # pytest suite
  frontend/
    src/
      api/        # fetch client
      context/       # auth context
      components/     # shared UI (header, footer, badges, empty states)
      pages/        # public, farmer, dealer, staff pages
      styles/       # design-system.css
  docs/         # role guide, production checklist, test report, known limitations
  ops/
    prometheus/     # scrape config + alert rules
    grafana/        # provisioned datasource + starter dashboard
    backups/        # backup_db.sh / restore_db.sh (pg_dump to S3)
  infra/
    terraform/      # AWS: ECS Fargate + RDS + ElastiCache + S3 + ALB
    k8s/          # Kubernetes: Deployment/HPA/Ingress/backup CronJob
  .github/workflows/ci.yml   # test -> build -> (approval-gated) deploy
  docker-compose.yml
  setup_windows.ps1 / start_windows.ps1
```

## Local setup (Linux/macOS)

```bash
# Backend
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env               # edit as needed; SQLite works out of the box
python -m scripts.doctor           # checks for common local problems
python -m scripts.upgrade_database # applies Alembic migrations
python -m scripts.seed_required_data   # seeds ONLY required setting keys, no fake data
python -m scripts.create_superadmin --email you@example.com --name "Your Name"
uvicorn app.main:app --reload      # http://localhost:8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev                        # http://localhost:5173
```

## Local setup (Windows)

```powershell
.\setup_windows.ps1
# then, once, create your first admin:
cd backend; .\.venv\Scripts\Activate.ps1
python -m scripts.create_superadmin --email you@example.com --name "Your Name"
cd ..
.\start_windows.ps1
```

`start_windows.ps1` runs the backend **without** `--reload`, avoiding a
known Windows issue where the uvicorn reload subprocess dies silently.

## Docker

```bash
cp backend/.env.example .env   # set SECRET_KEY at minimum
docker compose up --build
# frontend: http://localhost
# backend:  http://localhost:8000/api/v1/health
```

`docker-compose.yml` runs PostgreSQL, applies migrations automatically on
backend container start, and serves the built frontend behind nginx, which
proxies `/api/` to the backend.

## Tests

```bash
# Backend (49 tests)
cd backend && source venv/bin/activate && pytest -v

# Frontend unit tests
cd frontend && npm run test

# Frontend end-to-end (Playwright) - needs a running backend and a built
# frontend served separately; see .github/workflows/ci.yml's e2e-tests job
# for the exact sequence, or:
cd frontend && npx playwright install --with-deps chromium && npm run build
npx vite preview --port 5173 &
E2E_BASE_URL=http://localhost:5173 npm run e2e
```

See `docs/TEST_REPORT.md` for the current results.

## Deployment (actual production setup: Vercel + Render + Supabase + Brevo)

This is how the project is actually deployed today — not the only path it
supports (see "Alternative deployment paths" below), but the real one.

**Frontend — Vercel.** Git-linked to this repository's `main` branch (root
directory `frontend`): a plain `git push origin main` triggers a real
production build and deploy automatically. `frontend/vercel.json` provides
the SPA catch-all rewrite direct-navigation routing needs.
`frontend/.env.production` sets `VITE_API_BASE_URL` to the backend's
public URL (not a secret — it's a public URL, safe to commit).

**Backend — Render Web Service.** Python runtime, build command
`cd backend && pip install -r requirements.txt`, start command
`cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Unlike
the frontend, Render's git integration on this project does not reliably
auto-deploy on push — trigger a deploy manually from the Render dashboard
(or via the Render API) after pushing. See `render.yaml` for the full
service definition (no secrets in it — every secret is `sync: false` and
must be set in the Render dashboard directly).

**Database — Supabase Postgres.** Set `DATABASE_URL` to the connection
string from Supabase dashboard → Project Settings → Database → Connection
string (URI). Migrations run the same way as any other Postgres target:
`alembic upgrade head` (see "Local setup" above) — apply this against the
Supabase database *before* traffic hits a new schema version. This
project's Alembic chain has been verified to apply cleanly to Postgres via
an offline dry run (`alembic upgrade head --sql`), but running it against
the real Supabase instance is a manual, deliberate step — it is not run
automatically on deploy.

**File storage — Supabase Storage.** Set `SUPABASE_URL` and
`SUPABASE_SERVICE_ROLE_KEY` (see `backend/.env.example`) to switch
`app/core/storage.py` from local disk to Supabase Storage. Leave both
unset to keep using local disk (fine for development, NOT persistent
across Render redeploys in production).

**Email — Brevo.** Set `BREVO_API_KEY`, `EMAIL_FROM_EMAIL` (must be a
sender verified in the Brevo dashboard → Settings → Senders — Brevo
rejects sends from an unverified sender outright, there is no sandbox
fallback), and `EMAIL_PROVIDER_ENABLED=true`.

**Custom domain.** Not yet configured — the site runs on Vercel's and
Render's own subdomains today. When a custom domain is added: point its
DNS at the target Vercel/Render provides in each platform's domain
settings UI (a CNAME or A record, whichever that platform's own domain
page specifies at the time), update `CORS_ORIGINS` on the backend to
include the new frontend origin, and update `frontend/.env.production`'s
`VITE_API_BASE_URL` if the backend also moves to a custom domain. Don't
flip DNS until you've confirmed the exact target values in each
platform's dashboard — they're assigned per-project, not fixed in advance.

**Required production environment variables** (see `backend/.env.example`
for the full list with descriptions): `ENVIRONMENT=production`,
`SECRET_KEY`, `DATABASE_URL`, `COOKIE_SECURE=true`, `SUPABASE_URL`,
`SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_STORAGE_BUCKET`, `BREVO_API_KEY`,
`EMAIL_FROM_EMAIL`, `EMAIL_FROM_NAME`, `EMAIL_PROVIDER_ENABLED=true`,
`DEV_EXPOSE_OTP=false`, `DEV_EXPOSE_RESET_TOKEN=false`, `CORS_ORIGINS`
(the frontend's real origin(s)). The app refuses to start at all if
`ENVIRONMENT=production` and any of `SECRET_KEY`/`COOKIE_SECURE`/
`DEV_EXPOSE_OTP`/`DEV_EXPOSE_RESET_TOKEN` are left at an insecure value —
see `app/core/config.py`'s `_validate_production_settings`.

### Alternative deployment paths (supported, not currently used)

- **Docker Compose** (`docker-compose.yml`) — a self-contained
  Postgres+Redis+backend+nginx-fronted-frontend stack for a single-box
  deployment or local integration testing. Migrations run automatically
  on backend container start (see the backend `Dockerfile`'s `CMD`).
- **AWS** (`infra/terraform/`: ECS Fargate, RDS, ElastiCache, S3, ALB) or
  **Kubernetes** (`infra/k8s/`) — see `infra/terraform/README.md`.
  `.github/workflows/ci.yml`'s `build-and-push-images`/`deploy-production`
  jobs target this path specifically; they are inert (no-op / fail
  harmlessly) unless `AWS_DEPLOY_ROLE_ARN` etc. are configured as GitHub
  Actions secrets, which they are not for the actual Vercel/Render
  deployment above.
- **Monitoring:** `docker compose --profile monitoring up` runs Prometheus
  + Grafana locally against the backend's `/metrics` endpoint
  (`METRICS_ENABLED=true`); `ops/prometheus/alert_rules.yml` has starter
  alert rules for error rate, latency, and uptime.
- **Error tracking:** set `SENTRY_DSN` (backend) / `VITE_SENTRY_DSN`
  (frontend) to enable Sentry; both are no-ops until configured.
- **Backups:** `ops/backups/backup_db.sh` / `restore_db.sh` (written for a
  self-managed Postgres); against Supabase, use Supabase's own
  dashboard-driven backups/point-in-time-recovery instead (Project
  Settings → Database → Backups).

Full checklist: `docs/PRODUCTION_CHECKLIST.md`.

### Troubleshooting

- **`/api/ready` returns 503** — check the `database` field in its JSON
  response; a Supabase project can be paused (free tier) or `DATABASE_URL`
  can be wrong. `/api/health` only checks the process is up, not the DB.
- **Signup/reset emails never arrive** — confirm `EMAIL_PROVIDER_ENABLED=true`,
  `BREVO_API_KEY` is set, and `EMAIL_FROM_EMAIL` is verified as an active
  sender in the Brevo dashboard (Settings → Senders) — an unverified
  sender is rejected outright, with no partial delivery.
- **Uploaded files disappear after a redeploy** — `SUPABASE_URL`/
  `SUPABASE_SERVICE_ROLE_KEY` aren't set, so `app/core/storage.py` fell
  back to the container's local disk, which Render does not persist
  across deploys.
- **App won't start at all in production** — check the startup log for
  "Refusing to start with ENVIRONMENT=production and insecure settings" —
  it names exactly which setting(s) to fix.
- **A frontend request fails with a CORS error only when logged in** — see
  the CSRF/cross-origin note in `docs/SECURITY.md`; check that
  `CORS_ORIGINS` includes the frontend's exact origin.

## First Super Administrator

Staff accounts are never self-registered (see spec: no public role
selection for staff). The very first Super Administrator is created with:

```bash
python -m scripts.create_superadmin --email you@example.com --name "Your Name"
```

You will be prompted for a password (not passed on the command line, so it
never lands in shell history). From there, invite further staff via
`POST /api/v1/staff/invite` (Super Administrator/Administrator only), which
creates a temporary password and forces a change on first login.

## Environment variables

See `backend/.env.example` for every variable and a description of what it
does. The values that MUST change before production are called out in
`docs/PRODUCTION_CHECKLIST.md`.

## Backup and restoration

- **PostgreSQL:** use `pg_dump`/`pg_restore` (or your managed database
  provider's snapshot feature) against the `DATABASE_URL` target. This is
  standard PostgreSQL tooling; nothing in this app is exempt from it.
- **Uploaded files:** back up the `uploads/` volume (or your configured
  cloud storage bucket) alongside the database — media records reference
  file paths, and a database restore without the matching files will leave
  broken references.
- Always test a restore in a non-production environment before relying on
  a backup.

## Upgrade process

```bash
git pull
cd backend && source venv/bin/activate && pip install -r requirements.txt
python -m scripts.upgrade_database    # never deletes data automatically
cd ../frontend && npm install && npm run build
```

## Known limitations

See `docs/KNOWN_LIMITATIONS.md`.

## Documentation

- `docs/ROLE_GUIDE.md` — every role and what it can/cannot do.
- `docs/FARMER_GUIDE.md`, `docs/DEALER_GUIDE.md`
- `docs/STAFF_GUIDE.md` — product publishing, certificate
  verification/upload, agriculture photo management, and farmer rating
  moderation workflows.
- `docs/PRODUCTION_CHECKLIST.md`
- `docs/TEST_REPORT.md`
- `docs/KNOWN_LIMITATIONS.md`
- `docs/SECURITY.md`
- `CHANGELOG.md`
