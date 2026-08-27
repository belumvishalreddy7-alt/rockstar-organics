#!/usr/bin/env bash
# Dumps the production PostgreSQL database and uploads it to S3 (or any
# S3-compatible store). Intended to run on a schedule (cron / systemd timer
# / a Kubernetes CronJob - see infra/k8s/cronjob-backup.yaml).
#
# Required environment variables:
#   DATABASE_URL         postgresql://user:pass@host:5432/dbname
#   BACKUP_S3_BUCKET     e.g. s3://rockstar-organics-backups
# Optional:
#   BACKUP_RETENTION_DAYS  local temp-file retention before cleanup (default 1)
#   AWS_* / S3 credentials, provided by the environment/instance role as usual.
#
# Exits non-zero on any failure so the calling scheduler's own alerting
# (cron mailto, systemd OnFailure=, Kubernetes CronJob failure count) fires.
set -euo pipefail

: "${DATABASE_URL:?DATABASE_URL must be set}"
: "${BACKUP_S3_BUCKET:?BACKUP_S3_BUCKET must be set (e.g. s3://my-backups-bucket)}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-1}"

TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_DIR="$(mktemp -d)"
OUT_FILE="${OUT_DIR}/rockstar_organics_${TIMESTAMP}.sql.gz"

trap 'rm -rf "${OUT_DIR}"' EXIT

echo "[backup] dumping database..."
pg_dump --no-owner --no-acl "${DATABASE_URL}" | gzip -9 > "${OUT_FILE}"

echo "[backup] uploading to ${BACKUP_S3_BUCKET}/daily/${TIMESTAMP}.sql.gz"
aws s3 cp "${OUT_FILE}" "${BACKUP_S3_BUCKET}/daily/${TIMESTAMP}.sql.gz" --only-show-errors

echo "[backup] pruning local files older than ${RETENTION_DAYS} day(s)"
find "${OUT_DIR}" -type f -mtime "+${RETENTION_DAYS}" -delete || true

echo "[backup] done: ${TIMESTAMP}"
