# STAGE42 — Remove the unauthorized Saved Audits UI

## Scope

- Remove the **Saved audits · local history** expander from the Streamlit UI in **all** environments.
- In production, always choose the Neon/temporary token recovery pathway, even when `PAGECHECK_STORAGE_BACKEND` is absent or wrongly set. Do not fall back to SQLite history UI.
- Preserve the existing same-browser 24-hour recovery from `localStorage` and Neon. The browser holds a single unguessable token; no history index/list is exposed.
- Keep existing local-only SQLite API operations for compatibility with the local development workflow; they are forbidden in production by `history.py` and are **not** exposed in the Streamlit UI.
- Do not change the API deployment/image, report design, or enable public URL auditing.

## Privacy boundary

Different visitors using separate browser profiles do not share a recovery token. However, **anyone using the same browser profile on the same device can revisit the previous report**, because there is no user login. Preventing access on shared devices while persisting on browser close would require an additional identity/access-control requirement; this patch does not claim to provide it.

## Install

Extract the ZIP over the project root. Run `uv run pytest -q`. Only two paths are updated:

- `src/pagecheck/ui/app.py`
- New tests at `tests/unit/test_stage42_remove_shared_history_ui.py`

The document is informative, not a runtime dependency.

After tests pass, commit locally. Rebuild **only the UI** image using `deploy/Dockerfile.ui` and push it to the **existing private** Docker Hub repository with a new `stage42-ui` tag. Then change only Render `pagecheck-ui` Image Source from `stage40-ui` to `stage42-ui` and redeploy. Leave `pagecheck-api` at `stage41-api` and keep public auditing disabled.

## Verify

Open the hosted UI in an incognito browser. The `Saved audits` expander must not appear. Refresh/close/reopen the same browser profile after a saved audit is available to check recovery. The audit button remains disabled until the separate security release gate is genuinely satisfied.
