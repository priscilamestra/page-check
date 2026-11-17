#!/bin/sh
set -eu

# Render Free cannot run paid pre-deploy commands or a private API service.
# The existing SQL migration is idempotent and executes before Uvicorn starts.
: "${PAGECHECK_DATABASE_URL:?Neon PostgreSQL URL is required}"
: "${PAGECHECK_PRIVATE_API_KEY:?Server-to-server key is required}"
if [ "${PAGECHECK_ENV:-}" != "production" ]; then
    echo 'Render Free API must start in production mode' >&2
    exit 1
fi
/app/.venv/bin/python /app/scripts/postgres_temporary_migrate.py
# Expired records are inaccessible after 24h by query condition; physical
# deletion is opportunistic (startup plus save), without a paid cron service.
/app/.venv/bin/python /app/scripts/postgres_temporary_cleanup.py
exec /app/.venv/bin/uvicorn main:app --host 0.0.0.0 \
    --port "${PORT:-10000}" --workers 1
