# Production Checklist

## Application configuration

- [ ] `SECRET_KEY` replaced with a long random value (not the dev default) -
      inject it from a real secrets manager (see "Secrets management"
      below), never a plain `.env` committed anywhere.
- [ ] `ENVIRONMENT=production` set.
- [ ] `DEV_EXPOSE_RESET_TOKEN=false` (this is enforced in code regardless
      of the flag once `ENVIRONMENT=production`, but set it explicitly).
- [ ] `COOKIE_SECURE=true` (requires HTTPS).
- [ ] `DATABASE_URL` points to a PostgreSQL instance, not SQLite.
- [ ] Custom domain configured and `CORS_ORIGINS` updated to match.
- [ ] Email/SMS/WhatsApp provider connected if you want external
      notifications (see `app/core/notify.py` and `.env.example`).

## Secrets management

- [ ] No real secret (SECRET_KEY, DATABASE_URL password, REDIS_URL,
      SENTRY_DSN auth token) lives in a committed file, a Docker image
      layer, or a CI log. `.env` / `.env.local` are gitignored - keep it
      that way.
- [ ] Secrets are injected at deploy time from a managed store:
      - **Kubernetes** — see `infra/k8s/secret.example.yaml`. Prefer the
        External Secrets Operator pulling from AWS Secrets Manager/Vault
        over a hand-run `kubectl create secret` once you have more than
        one environment.
      - **ECS/Terraform** — `infra/terraform/ecs.tf` deliberately omits
        `SECRET_KEY` from the plain task-definition environment; wire it
        through the task definition's `secrets` block pointing at an AWS
        Secrets Manager ARN instead, and consider
        `manage_master_user_password = true` on the RDS resource in
        `infra/terraform/database.tf` so AWS generates/rotates the DB
        password for you.
      - **CI** — `.github/workflows/ci.yml` reads `AWS_DEPLOY_ROLE_ARN`,
        `SENTRY_AUTH_TOKEN`, etc. from GitHub Actions repository/environment
        secrets, never from a file in the repo.
- [ ] A secret-rotation owner and cadence is documented (who rotates
      `SECRET_KEY`/DB credentials/Sentry tokens, and how often).

## Database & backups

- [ ] Database backups configured and a restore has been tested. See
      `ops/backups/backup_db.sh` (scheduled via `infra/k8s/cronjob-backup.yaml`
      on Kubernetes, or RDS's own automated backups when using
      `infra/terraform/database.tf`, which sets a 14-day retention window
      and Multi-AZ in production).
- [ ] Restore process tested end-to-end in a non-production environment
      using `ops/backups/restore_db.sh` against a scratch database - never
      the first time during an actual incident.
- [ ] Migrations applied (`alembic upgrade head` — see `scripts/`) as part
      of every deploy, before the new application version starts serving
      traffic.

## File storage

- [ ] `uploads/` (or your cloud storage adapter) is on persistent,
      backed-up storage, not container-ephemeral disk. `infra/terraform/storage.tf`
      provisions an encrypted, versioned S3 bucket for this; the Kubernetes
      path (`infra/k8s/backend-deployment.yaml`) uses a ReadWriteMany PVC as
      a portable fallback — prefer S3 if your cluster/cloud supports it.

## Hosting & scaling

- [ ] Deployed via one of the provided paths rather than a single
      hand-run container: `infra/terraform/` (AWS: ECS Fargate + RDS +
      ElastiCache + S3 + ALB, see `infra/terraform/README.md`) or
      `infra/k8s/` (any Kubernetes cluster: Deployments, HPA, Ingress,
      backup CronJob).
- [ ] `REDIS_URL` is set in every production environment with more than
      one backend worker/instance. Without it, `app/core/rate_limit.py`
      falls back to an in-memory limiter that under-counts across
      processes — check `/api/v1/ready`, which reports `"redis": "configured
      but limiter fell back to in-memory at startup"` if this is
      misconfigured.
- [ ] Horizontal scaling verified: the backend is stateless (sessions are
      signed cookies, not server-side session storage) so it scales by
      adding replicas — `infra/terraform/ecs.tf` autoscales 3-12 tasks on
      CPU, `infra/k8s/backend-deployment.yaml`'s HPA does the same.
- [ ] TLS terminates at the load balancer/ingress (ALB + ACM in
      `infra/terraform/ecs.tf`, or `cert-manager` in
      `infra/k8s/frontend-deployment.yaml`'s Ingress annotations) — never
      served over plain HTTP in production.

## CI/CD

- [ ] `.github/workflows/ci.yml` is green on `main`: backend pytest,
      frontend typecheck/vitest/build, and the Playwright E2E smoke suite
      all pass before any image is built.
- [ ] Container images are built and pushed to your registry only after
      every test stage passes (see the `build-and-push-images` job's
      `needs:` list) — a red test run never produces a deployable image.
- [ ] The `deploy-production` job is gated behind a GitHub Environment
      named `production` with required reviewers configured, so a push to
      `main` builds and tests automatically but does not deploy to
      production without an explicit approval. Adjust this gate to match
      your team's actual release process.
- [ ] Registry credentials/deploy role (`AWS_DEPLOY_ROLE_ARN`,
      `AWS_REGION`) are configured as repository/environment secrets, not
      hardcoded in the workflow file.

## Error tracking & monitoring

- [ ] `SENTRY_DSN` set on the backend and `VITE_SENTRY_DSN` set on the
      frontend build if you want error tracking — both are opt-in and
      inert until configured (see `.env.example` in each package).
- [ ] `SENTRY_AUTH_TOKEN` / `SENTRY_ORG` / `SENTRY_PROJECT` configured as
      GitHub Actions secrets if you want release tracking
      (`.github/workflows/ci.yml`'s `notify-sentry-release` job).
- [ ] `METRICS_ENABLED=true` set and `/metrics` is reachable only from your
      Prometheus scraper (private network/security group), never exposed
      publicly — it carries no application-layer authentication.
- [ ] Prometheus + Grafana running (`docker-compose --profile monitoring up`
      for a single-box deployment, or point an existing cluster Prometheus
      at the backend Service using `infra/k8s/backend-deployment.yaml`'s
      labels) and scraping `/metrics` — see `ops/prometheus/prometheus.yml`.
- [ ] Alert rules (`ops/prometheus/alert_rules.yml`: high 5xx rate, high
      p95 latency, backend down, `/api/v1/ready` failing) are wired to a real
      Alertmanager receiver (Slack/PagerDuty/email) — the rules file alone
      doesn't deliver notifications until Alertmanager is configured.
- [ ] `/api/v1/health` (liveness) and `/api/v1/ready` (readiness — checks the
      database, and Redis when configured) are wired into your
      orchestrator's health checks (already done in
      `infra/k8s/backend-deployment.yaml` and `infra/terraform/ecs.tf`'s
      target group health check).

## Testing

- [ ] Backend tests passing (`pytest`, currently 42/42).
- [ ] Frontend unit tests passing (`npm run test`).
- [ ] Frontend production build succeeds (`npm run build`).
- [ ] Playwright E2E smoke suite passing against a real backend
      (`npm run e2e` — see `frontend/e2e/smoke.spec.ts` and
      `frontend/playwright.config.ts`). This is what actually caught a
      real bug during this pass (a blank optional email field was
      rejected by the enquiry API) that unit tests alone missed — run it
      before every release, not just once.

## Content & compliance

- [ ] All starter legal text (`docs/*`, public legal pages) reviewed by a
      qualified professional before publishing.
- [ ] All product claims reviewed against actual label/regulatory
      documentation before publishing any product.
- [ ] Staff accounts verified and unnecessary accounts removed.
- [ ] Every staff account's initial/temporary password has been changed
      (the app now enforces this automatically via the
      `must_change_password` gate - see `docs/SECURITY.md`).

## Final review

- [ ] Basic security review completed (headers present, CSRF enforced,
      rate limits sane for your expected traffic, dependency versions
      current — see `docs/SECURITY.md`).
- [ ] Logging configured for the production log stream (structured JSON
      logs are emitted to stdout — pipe to your log aggregator/CloudWatch/
      whatever ingests container stdout in your environment).
- [ ] Restore process tested end-to-end in a non-production environment
      (duplicate of the database bullet above — intentionally listed
      twice; it's the check most often skipped).
