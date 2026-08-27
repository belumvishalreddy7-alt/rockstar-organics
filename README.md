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
- Real (not mocked) transactional email via Resend (`app/core/email.py`):
  OTP codes, password resets, welcome emails, and dealer/distributor
  approval credentials. Verified live against the real Resend API — see
  `docs/SECURITY.md` for the exact result: the integration itself works,
  but delivery needs a verified sending domain on the connected Resend
  account before mail actually lands in an inbox.
- Development demo accounts for all roles (`backend/scripts/
  seed_demo_accounts.py`); refuses to run when `ENVIRONMENT=production`.

## Technology stack

- **Backend:** Python 3.11+, FastAPI, SQLAlchemy 2, Alembic, Pydantic v2,
  Argon2 password hashing, itsdangerous session cookies.
- **Frontend:** React 19, TypeScript, Vite, React Router, TanStack Query,
  a custom CSS design system (no component-library default styling).
- **Database:** PostgreSQL in production; SQLite is supported for local
  development using the same SQLAlchemy models and Alembic migrations.
- **Testing:** Pytest (backend, 49 tests), Vitest (frontend component
  tests), Playwright (end-to-end browser smoke tests, 9 tests).
- **Ops:** GitHub Actions CI/CD, Sentry error tracking, Prometheus +
  Grafana monitoring, Redis-backed rate limiting, Terraform (AWS) and
  Kubernetes deployment manifests — see `docs/PRODUCTION_CHECKLIST.md`.

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

## Production deployment, monitoring & backups

- **CI/CD:** `.github/workflows/ci.yml` runs the full test suite (backend,
  frontend, E2E) on every push/PR, builds and pushes Docker images once
  everything passes, and deploys to production only behind an
  approval-gated GitHub Environment.
- **Hosting:** `infra/terraform/` (AWS: ECS Fargate, RDS, ElastiCache,
  S3, ALB — see `infra/terraform/README.md`) or `infra/k8s/` (any
  Kubernetes cluster).
- **Monitoring:** `docker compose --profile monitoring up` runs Prometheus
  + Grafana locally against the backend's `/metrics` endpoint
  (`METRICS_ENABLED=true`); `ops/prometheus/alert_rules.yml` has starter
  alert rules for error rate, latency, and uptime.
- **Error tracking:** set `SENTRY_DSN` (backend) / `VITE_SENTRY_DSN`
  (frontend) to enable Sentry; both are no-ops until configured.
- **Backups:** `ops/backups/backup_db.sh` / `restore_db.sh`, scheduled via
  `infra/k8s/cronjob-backup.yaml` or RDS's own automated backups.

Full checklist: `docs/PRODUCTION_CHECKLIST.md`.

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
- `docs/FARMER_GUIDE.md`, `docs/DEALER_GUIDE.md`, `docs/STAFF_GUIDE.md`
- `docs/PRODUCTION_CHECKLIST.md`
- `docs/TEST_REPORT.md`
- `docs/KNOWN_LIMITATIONS.md`
- `docs/SECURITY.md`
- `CHANGELOG.md`
#   r o c k s t a r - o r g a n i c s  
 #   r o c k s t a r - o r g a n i c s  
 #   r o c k s t a r - o r g a n i c s  
 