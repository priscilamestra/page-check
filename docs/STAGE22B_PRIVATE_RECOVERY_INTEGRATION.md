# Page Check — Stage 22B: private PostgreSQL recovery integration

## What is implemented

Stage 22A already created PostgreSQL JSONB and BYTEA storage, 24-hour expiration,
hashed bearer tokens, and the migration. Stage 22B wires it **optionally** to:

- FastAPI: server-to-server POST endpoints for `save`, `restore`, `image`, `revoke` under `/v1/temporary`.
- Streamlit: `PAGECHECK_STORAGE_BACKEND=postgres_temporary` switches the UI from
  SQLite's multi-audit local history to **one most-recent, recoverable report**.
- Browser: a small trusted Streamlit V2 component saves a **single 43-character
  bearer token in origin-scoped `localStorage`**, never in a URL query or fragment.
  An F5 resets the Streamlit session but the component reads the token back and
  restores the audit without re-running the scanner.
- Screenshots: API serves guarded PNG bytes from PostgreSQL. Streamlit temporarily
  copies them into its own `artifacts/temporary_restore` tree so screenshots and
  ZIP export work even when the Render web/API services have separate disks.
- An explicit "Forget this audit on this browser" action revokes the recovery
  token and clears browser storage. Database expiration remains 24 hours.

**No login, persistent user registry, public audit listing or permanent history.**
The old SQLite history is unchanged when `PAGECHECK_STORAGE_BACKEND` is unset.

## Important environment variables

| Service | Setting | Purpose |
| --- | --- | --- |
| FastAPI | `PAGECHECK_DATABASE_URL` | Private PostgreSQL connection string, from Neon |
| Streamlit | `PAGECHECK_STORAGE_BACKEND=postgres_temporary` | Enables this recovery flow in the UI |
| Streamlit | `PAGECHECK_API_URL` | URL of the FastAPI service, not the browser's URL |
| Both services | `PAGECHECK_PRIVATE_API_KEY` | **Same** random secret of at least 32 characters for server-to-server POST calls |
| Both services (local only) | `PAGECHECK_ENV=development` | Opt-in local testing; the production scanner remains disabled by default |

No database URL or private API key belongs in source control, a browser URL,
or Streamlit output. Configure them through environment variables/secrets.

## Local validation order

1. Commit Stage 22A separately, after checking the staged paths.
2. Install the 22B ZIP and run `uv run pytest -q`. If there were exactly 482 tests before
   installing, **493 tests are expected** (11 new unit tests).
3. Without Neon credentials, you may continue using SQLite locally. The 22B
   tests use a fake store and mocked requests: **passing them does not prove
   database connectivity or browser behavior**.
4. Create a private PostgreSQL database in Neon. Do **not** paste credentials
   into chat or commit them. With `PAGECHECK_DATABASE_URL` set only in the
   FastAPI/migration terminal, run:

   ```powershell
   uv run python scripts/postgres_temporary_migrate.py
   uv run python scripts/postgres_temporary_smoke.py
   ```

5. Run FastAPI locally (with your existing guarded local audit opt-ins) and
   Streamlit with `PAGECHECK_STORAGE_BACKEND=postgres_temporary`.
   Set `PAGECHECK_PRIVATE_API_KEY` on **both** services if using the key in
   local testing; a matching secret is mandatory for nonlocal requests.
6. Run a public test-page audit; verify recovery after F5, browser reopening,
   and a FastAPI restart, including screenshot and ZIP export. Verify that
   a different browser profile cannot open the report; replacing the audit
   revokes the previous token.
7. Verify expiration and actual scheduled cleanup (not only rejection after
   24 hours) before deploying.

## Security/deploy status

This is a **development integration**, not approval for public hosting.
Public scanner execution remains blocked by the Stage 20 production gate.
The `POST /v1/temporary/*` routes are private: remote requests require the
server-only `PAGECHECK_PRIVATE_API_KEY` and there is **no GET listing route**.

The recovery token is a bearer secret, stored in browser `localStorage`. It
is not available in browser URLs, referrer headers, or ordinary HTTP URL logs.
However, malicious JavaScript from the **same app origin**, browser extensions,
or anyone with access to the user's browser profile can access localStorage.
Do not inject untrusted HTML/JS or enable arbitrary scripts. Use HTTPS for
both services, rate and concurrency limits, egress isolation, a data retention
policy, and a monitored cleanup job before public deploy. Report data are not
anonymous by default: scanned URLs and screenshots may be sensitive.

The older SQLite `/v1/history` API remains **local-only**. In production, do
not configure the Streamlit interface to show the local history.

## Limitations to validate before committing 22B

The JavaScript bridge is covered by static/contract checks only, not by a
real-browser end-to-end test in this delivery. A running Neon database and a
browser are required to validate recovery across F5 and restarts. The
preexisting Impeccable output compatibility issue and Playwright deployment
safety remain separate pending work.
