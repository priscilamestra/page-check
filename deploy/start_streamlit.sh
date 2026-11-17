#!/bin/sh
set -eu

# Render Blueprint resolves the private API host:port. Its value stays on
# Render's internal network; the browser never receives this connection URL.
: "${PAGECHECK_API_HOSTPORT:?Render private API hostport is required}"
: "${PAGECHECK_PRIVATE_API_KEY:?Shared server-to-server API key is required}"

case "$PAGECHECK_API_HOSTPORT" in
    *://*|*/*|*' '*|*'@'*|*'?'*|*'#'*)
        echo 'Invalid internal API hostport configuration' >&2
        exit 1
        ;;
esac
export PAGECHECK_API_URL="http://${PAGECHECK_API_HOSTPORT}"

exec /app/.venv/bin/streamlit run streamlit_app.py \
    --server.address=0.0.0.0 \
    --server.port="${PORT:-10000}" \
    --server.headless=true \
    --browser.gatherUsageStats=false
