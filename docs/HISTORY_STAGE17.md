# Page Check — Stage 17: SQLite history & portable exports

## Scope

Local-first history for the existing `audit-report-1.0` report. No new audit engines, model APIs, user accounts, or OAuth. The UI stays in English; content-language selection remains independent of history.

**Deliverables:**

- SQLite index under `data/local/pagecheck_history.sqlite3`.
- Full JSON snapshots under `data/local/history/<audit_id>/report.json`.
- Screenshot copies under `artifacts/history/<audit_id>/` (if original local PNGs exist).
- Saved-audit list, open, and confirmed deletion in the Streamlit **Saved audits · local history** section.
- Automatic save *after successful live audits*. Importing or opening sample data does not silently create a new history record.
- Downloads in the **Data** tab: original JSON, findings CSV, portable HTML + available screenshots ZIP.
- Local-only API for history actions, with no impact on `/v1/audits/page` or existing SEO endpoints.

These folders are already excluded by `.gitignore`; do not commit user reports or screenshots. Never place API keys, OAuth tokens, or personal information in source control. URLs can contain sensitive query parameters, so treat saved reports as private.

## Endpoints (FastAPI running on 127.0.0.1)

| Method | Path | Behavior |
| --- | --- | --- |
| POST | `/v1/history` | Save an existing consolidated report; returns new audit ID |
| GET | `/v1/history?limit=20&offset=0` | List saved metadata in newest-first order |
| GET | `/v1/history/{audit_id}` | Load saved report and its screenshot references |
| GET | `/v1/history/{audit_id}/export?format=json` | Download JSON |
| GET | `/v1/history/{audit_id}/export?format=csv` | Download CSV of findings |
| GET | `/v1/history/{audit_id}/export?format=html_zip` | Download HTML + PNG ZIP |
| DELETE | `/v1/history/{audit_id}` | Remove one saved report and its copied evidence |

History endpoints require the connecting client's address to be loopback. This is a **single-computer development implementation**, not an authenticated multi-user service. A public deployment requires authentication, authorization, CSRF/origin protections as applicable, secrets handling, network isolation, retention controls and an access-control review. Do not forward these endpoints to the internet as-is.

`POST /v1/history` stores reports **already produced by existing audits**. It does not start a new audit or use network access, and it is not the previously proposed queued `/v1/audits` job API.

## Run and verify

```powershell
# No new Python or Node dependencies are needed.
uv run pytest tests/unit/test_history_store.py tests/unit/test_report_exports.py tests/integration/test_history_api.py -v
uv run pytest -q

# Offline fixture; writes one new history entry and two export files.
uv run python scripts/history_fixture_smoke.py
explorer.exe .\artifacts\history_stage17
```

The offline fixture prefers Stage 16D's consolidated report and falls back to Stage 15's reference report. If neither exists, run the appropriate fixture-generator script as instructed by the smoke script.

Start/restart both local servers to check the UI:

```powershell
# Terminal 1
$env:PAGECHECK_ALLOW_LIVE_FETCH="1"  # development only
uv run uvicorn main:app --reload --host 127.0.0.1 --port 8000

# Terminal 2
uv run streamlit run streamlit_app.py
```

In Streamlit, open **Saved audits · local history**, select a record and choose **Open saved audit**. Verify that screenshots appear in **Screenshots** when the stored record has local PNG evidence. In **Data**, download the CSV or HTML ZIP and open `report.html` from the extracted ZIP. Saving a live run is automatic; it is *not* necessary to click a second Save button.

## Limits and decisions

- SQLite stores indexed metadata, not screenshot blobs. Reports are immutable snapshots with random UUID-based IDs.
- Report files are limited to 5 MB; each screenshot copy is limited to 20 MB; screenshot paths must resolve under `artifacts/`. External or missing PNGs are not copied.
- ZIP export only includes confirmed local images. A missing screenshot is not claimed to have been tested.
- CSV values beginning with spreadsheet formula syntax are escaped to prevent formula execution when opened in spreadsheet software.
- History works on a single machine and is not a replacement for a production user-account database.
- PDF is outside the original PRD; the portable deliverable is an accessible HTML report plus CSV/JSON/PNGs in one ZIP.
- Final UI/Overview/visual-findings refinements remain planned **after Stage 18**, as agreed. This update intentionally makes no layout redesign.
