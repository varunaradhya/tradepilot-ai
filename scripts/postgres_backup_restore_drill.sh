#!/usr/bin/env bash
set -euo pipefail

# Safe PostgreSQL backup/restore drill.
# Required:
#   TRADEPILOT_PGURL        PostgreSQL libpq URL for the source database.
#   TRADEPILOT_RESTORE_PGURL PostgreSQL libpq URL for a dedicated restore target.
# Optional:
#   BACKUP_FILE             Output path (default: ./tradepilot-backup.dump)
#
# This script never restores over the source URL. The target must be explicitly
# supplied and CONFIRM_RESTORE=YES is required before destructive target work.

: "${TRADEPILOT_PGURL:?Set TRADEPILOT_PGURL to the source PostgreSQL URL}"
: "${TRADEPILOT_RESTORE_PGURL:?Set TRADEPILOT_RESTORE_PGURL to a dedicated restore target}"
BACKUP_FILE="${BACKUP_FILE:-./tradepilot-backup.dump}"

if [[ "${TRADEPILOT_PGURL}" == "${TRADEPILOT_RESTORE_PGURL}" ]]; then
  echo "Refusing to restore into the source database." >&2
  exit 2
fi

command -v pg_dump >/dev/null || { echo "pg_dump is required." >&2; exit 2; }
command -v pg_restore >/dev/null || { echo "pg_restore is required." >&2; exit 2; }

echo "Creating custom-format backup: ${BACKUP_FILE}"
pg_dump --format=custom --no-owner --no-privileges --file="${BACKUP_FILE}" "${TRADEPILOT_PGURL}"

echo "Backup created. Validate it before any restore."
pg_restore --list "${BACKUP_FILE}" >/dev/null

if [[ "${CONFIRM_RESTORE:-NO}" != "YES" ]]; then
  echo "Backup verification complete. Set CONFIRM_RESTORE=YES to execute the restore drill against the dedicated target."
  exit 0
fi

echo "Restoring into dedicated target."
pg_restore --clean --if-exists --no-owner --no-privileges --dbname="${TRADEPILOT_RESTORE_PGURL}" "${BACKUP_FILE}"

echo "Restore completed. Run 'alembic upgrade head' against the restore target and execute the application smoke tests before declaring recovery successful."
