# Page Check: restore saved audit after browser refresh

This is a targeted Stage 18 correction. No audit engines, database schema, API routes, or report rendering logic are changed.

## Symptom

After opening **Saved audits → Open saved audit**, pressing F5 cleared the report view. The report remained stored in SQLite, and opening it manually worked again.

## Cause and fix

Streamlit `st.session_state` is not durable across a browser reload. The fix records **only the 32-character saved audit ID** in the browser URL as `?audit=<id>`. On a fresh session, the UI loads that exact audit from the local-only `/v1/history/<id>` API. No new audit is executed and no report data is placed in the URL.

Opening a different saved audit updates the ID. Starting a new audit, opening sample data, or importing a JSON clears the previous ID. Deleting the currently opened saved audit clears its report and URL ID.

## Validation

1. Ensure FastAPI and Streamlit are running on the local machine.
2. Open an older item under **Saved audits · local history**.
3. Check the browser URL includes `?audit=<32 hexadecimal characters>`.
4. Press F5. The same historical report should appear without clicking **Open saved audit** again.
5. Confirm the SQLite history count does not grow after F5.
6. Open another saved audit and repeat.
7. Delete the currently opened audit and verify the report and URL selection clear.

## Tests

```powershell
uv run pytest tests/unit/test_history_resume.py -v
uv run pytest -q
```

**Local-only:** the URL contains a non-secret opaque report ID, not the audit data. This does not replace authentication or make the history API suitable for public deployment.
