# STAGE38 — Hosted staging release: Render + Neon

This is the **final code-preparation step**, not approval for public URL scans.

## What changes

- `render.yaml`: adds an automated **pre-deploy database migration** for the
  Render private API. The existing migration uses `CREATE TABLE IF NOT EXISTS`
  to create the 24-hour recovery tables when missing.
- `pagecheck.ops.release_smoke`: verifies a *running* private API, service-key
  rejection/acceptance and Neon schema. It is read-only, does not run audits,
  and refuses to run if any public-scan flag is enabled.
- No UI changes, additional engines, or new network permissions.

## Local verification — no GitHub push

```powershell
uv run pytest -q
uv run python scripts/render_deploy_preflight.py
git status --short
git diff --check
git add -- render.yaml src/pagecheck/ops/__init__.py src/pagecheck/ops/release_smoke.py tests/unit/test_stage38_release_smoke.py docs/STAGE38_HOSTED_STAGING_RELEASE.md
git diff --cached --check
git commit -m "chore(deploy): automate Neon migration and hosted verification"
git status --short
```

## Actual release — requires user approval of GitHub push and Render costs

1. Inspect Render's Blueprint cost estimate before creation. Existing plans
   in `render.yaml` are paid (private API, web UI, hourly cleanup Cron).
2. User pushes only the final locally committed version to GitHub, then links
   that repo to Render Blueprint. No push is performed by this script.
3. In Render Dashboard, set `PAGECHECK_DATABASE_URL` for **API and Cron**.
   Do not commit Neon secrets or paste them in chat. API `preDeployCommand`
   initializes the database schema before the API boots.
4. Keep `PAGECHECK_PUBLIC_AUDITS_ENABLED=0`, `PAGECHECK_EGRESS_ISOLATED=0`,
   `PAGECHECK_ALLOW_LIVE_FETCH=0`, `PAGECHECK_ALLOW_LIVE_BROWSER=0`.
5. After services are healthy, open the private API's Render Shell and run:

   ```sh
   /app/.venv/bin/python -m pagecheck.ops.release_smoke
   ```

6. Success: `STAGE38_HOSTED_STAGING_SMOKE_PASSED`. Open the Streamlit public URL
   to check its connected badge and imported JSON report. **New URL auditing
   remains disabled in staging** and must not be advertised as functional.
7. Check that the cleanup Cron ran successfully and that no secrets appear in logs.

## Only remaining release blocker

Do NOT enable public audits merely because this staging test passed. Chromium's
kernel guard is verified locally, but Python's acquisition process can still
create outbound network sockets. Render's private service limits inbound
access, not general outbound egress. A verified independent network boundary
for Python fetches (or an isolated acquisition worker) and an E2E hosted audit
are mandatory to operate this product as a public URL auditing service.

If Render cannot provide the isolation required by this architecture, keep the
app as a private/staging preview or choose a genuinely isolated scanner host.
