# Stage 22A — PostgreSQL temporary-report repository (backend foundation)

## Scope

This increment introduces the database layer for **one recoverable audit per browser**, with a 24-hour retention window and screenshots stored as bounded PostgreSQL `BYTEA`. It deliberately **does not expose new HTTP routes or enable public URL scanning**. The existing local SQLite history remains unchanged for development. The new store is not yet connected to the Streamlit F5 flow.

### Stack

- Render will host Streamlit and FastAPI after production security work is complete.
- A private PostgreSQL instance (planned: Neon) will store short-lived reports (`JSONB`) and limited screenshot evidence (`BYTEA`).
- The database is PostgreSQL, accessed using standard SQL via `psycopg`; no provider-specific API is used.
- No login, public history list or permanent user account tables.

### Security contract

- A cryptographic 256-bit recovery token is generated using `secrets.token_urlsafe(32)` and returned to the trusted caller. **Only its SHA-256 digest is persisted**; never log the raw token.
- Loading and deleting an audit requires the full opaque token. Expired records cannot be read, and `DELETE` cascades to screenshots.
- Each new save can revoke a known `previous_token`, leaving only one active recovery token per browser when the caller supplies it. This cannot limit unrelated browsers without cookies or authentication.
- Report JSON is limited to 5 MB; PNG images to 2 MB each and 4 MB collectively. Screenshots must resolve inside the project's `artifacts/` folder and have the PNG signature. They are stored separately from JSON; original filesystem paths are not placed in `report['screenshots']`.
- No public route exists in Stage 22A. Future API/Streamlit wiring must prevent recovery tokens from leaking through browser history, request logs, referrers, or screenshots. The existing `?audit=...` local-history URL should **not** be reused unmodified for bearer tokens.
- Database credentials are server-only. Use `PAGECHECK_DATABASE_URL` in a private environment variable. Never put it in the UI, README, Git, or public client code.
- The production gate from Stage 20 remains active. **This is not a production-ready public scanner.**

### Setup (when the private Neon database exists)

```powershell
# Configure PAGECHECK_DATABASE_URL privately (do not paste the value into chat or screenshots).
uv sync
uv run python scripts/postgres_temporary_migrate.py
uv run python scripts/postgres_temporary_smoke.py
uv run python scripts/postgres_temporary_cleanup.py
```

The migration is additive and never deletes local SQLite history. Cleanup deletes only expired PostgreSQL records. `save()` also removes expired rows when an audit is written; it is **not a substitute for scheduled cleanup**. To guarantee physical deletion promptly after expiry, configure an authenticated scheduled job (e.g., Neon-supported database scheduling or secure external scheduler) and monitor its success.

### Next increment — Stage 22B

1. Add private, abuse-protected API routes for save/resume/export/revoke with no public list endpoint.
2. Store only one current recovery identifier in the browser; use a safe token transport instead of placing the bearer token in a URL query.
3. Serve screenshots via validated, token-protected endpoints or via the trusted Streamlit backend, using the stored bytes rather than paths on a shared disk.
4. Reuse the report/ZIP exports without exposing the temporary image references as filesystem paths.
5. Verify F5 and full Render restart, 24-hour expiry, deletion, isolated browsers and production safety in an end-to-end environment.

### UI follow-up recorded

The redundant "Live audits require the API server." text was removed from **Tools → Connection**. The two indicators are **FastAPI connected** (green) and **FastAPI disconnected** (gray), as requested. The next visual redesign remains deferred until infrastructure is closed.
