# Stage 18B — Browser-local history, top menu, detector schema compatibility

## Why

- The SQLite store contains timezone-aware instants in UTC (`created_at`). Keep this **unchanged**.
- The history selector formerly displayed UTC timestamps verbatim, even for users in Brazil.
- The original sidebar contained only API status and developer/sample controls, consuming unnecessary horizontal space.
- Some Impeccable detector versions use `rule_id` instead of `ruleId`.

## What changed

- Browser timezone is read from `st.context.timezone` (IANA name, DST-aware). A Windows installation without an IANA database can use `pytz`, which is already installed via Pandas. Offset fallback uses `st.context.timezone_offset`, and explicit UTC fallback prevents silent server-local mistakes.
- History labels use US format **MM/DD/YYYY · h:mm AM/PM (zone)**. Saved IDs, dates, sort order, APIs and exports are unchanged.
- Sidebar removed. `Connection & tools` native Streamlit popover sits at upper right *inside the page*, below Streamlit's own native Deploy toolbar. It includes connection status, Developer tools and the unchanged `Load sample report` action. There is **no login or account section**.
- In public deployment, **set `PAGECHECK_ENV=production`** to hide the Developer tools section and sample-report loader entirely from the Streamlit UI. The top control then reads `Connection`. Restrict or disable development-only backend endpoints separately; hiding UI is not security.
- Impeccable adapter recognizes explicit identifiers `rule_id`, `checkId`, `check_id` and nested `rule.key`. Unknown schemas still return **Not verified**, never invented results.

## Validation

```powershell
uv run pytest tests/unit/test_history_browser_timezone_stage18b.py tests/unit/test_impeccable_schema_stage18b.py -v
uv run pytest -q
```

Then restart Streamlit, open saved history, verify the label uses the browser local time, open a report, F5, check it remains selected, and use Connection & tools at the top of the page. It is *not* positioned inside Streamlit's built-in toolbar.

## Remaining

- The real Impeccable CLI output could have an additional schema not covered by these tests. Verify against the installed binary before claiming full integration.
- Public deployment requires an independent security review, including rate limiting, origin/reverse-proxy controls, safe browser/network sandboxing, and deployment-specific security testing. No account or login UI is included in this version.
- Full Overview/chart/Issues/screenshot redesign remains the next visual phase; no chart has been replaced in this stage.
