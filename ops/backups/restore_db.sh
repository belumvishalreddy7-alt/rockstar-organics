#!/usr/bin/env bash
# Restores a PostgreSQL dump produced by backup_db.sh.
#
# Usage:
#   ./restore_db.sh s3://rockstar-organics-backups/daily/20260825T030000Z.sql.gz
#
# ALWAYS restore into a fresh/staging database first and verify the app
# works against it before ever pointing production DATABASE_URL at a
# restored database. This script intentionally does not touch DATABASE_URL
# for you - pass the *target* connection string explicitly so a restore can
# never be run against the wrong database by mistake.
set -euo pipefail

SOURCE_S3_URI="${1:?Usage: restore_db.sh <s3://.../file.sql.gz> [target postgresql:// DSN]}"
TARGET_DSN="${2:-${RESTORE_TARGET_DATABASE_URL:?Set RESTORE_TARGET_DATABASE_URL or pass a target DSN as the 2nd argument}}"

TMP_FILE="$(mktemp)"
trap 'rm -f "${TMP_FILE}"' EXIT

echo "[restore] downloading ${SOURCE_S3_URI}"
aws s3 cp "${SOURCE_S3_URI}" "${TMP_FILE}" --only-show-errors

echo "[restore] restoring into target database (this DOES NOT drop existing objects - use a fresh database)"
gunzip -c "${TMP_FILE}" | psql "${TARGET_DSN}"

echo "[restore] done. Run the app's smoke tests against the target before promoting it to production."
