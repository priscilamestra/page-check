#!/bin/sh
set -eu
: "${PAGECHECK_DATABASE_URL:?Neon PostgreSQL URL is required}"
exec /app/.venv/bin/python scripts/postgres_temporary_cleanup.py
