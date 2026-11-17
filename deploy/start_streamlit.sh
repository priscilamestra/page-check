#!/bin/sh
set -eu

# Render Free provides two public Web Services. API calls originate on the
# Streamlit server, over HTTPS; the secret is never sent to the browser.
: "${PAGECHECK_PRIVATE_API_KEY:?Server-to-server authentication is required}"
: "${PAGECHECK_API_URL:?Public FastAPI HTTPS URL is required}"
case "$PAGECHECK_API_URL" in
    https://*) ;;
    *) echo 'FastAPI URL must use HTTPS in the Render Free deployment' >&2; exit 1 ;;
esac
api_host=${PAGECHECK_API_URL#https://}
case "$api_host" in
    ''|*/*|*' '*|*'@'*|*'?'*|*'#'*)
        echo 'Invalid FastAPI URL configuration' >&2; exit 1 ;;
esac

exec /app/.venv/bin/streamlit run streamlit_app.py \
    --server.address=0.0.0.0 \
    --server.port="${PORT:-10000}" \
    --server.headless=true \
    --browser.gatherUsageStats=false
