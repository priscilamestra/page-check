# Page Check — Stage 18: offline end-to-end validation gate

## Purpose

Verify that the already implemented API, audit orchestration, SQLite persistence,
report reopening, and JSON/CSV/HTML-ZIP exports work together, **without accessing
external URLs**. This is an integration gate, not a new auditor or a claim that
the entire MVP is production-ready.

## What the new test covers

- `POST /v1/audits/page` through the real FastAPI route and real HTML audit use case.
- One injected HTML GET; SEO, content language/keywords, and URL/conversion checks use the real code.
- A **controlled visual observation**, rather than launching a browser or accessing an external site.
- `POST /v1/history`: SQLite record and screenshot copy into a temporary project root.
- `GET /v1/history` and `GET /v1/history/{id}`: report can be reopened without re-fetching.
- `GET /v1/history/{id}/export`: JSON, CSV and ZIP containing HTML and both screenshot files.
- Negative gates: remote callers cannot access local history, and the remote-fetch opt-in remains mandatory.
- Engines not actually executed remain `not_verified`; Lighthouse scores remain unavailable.

The test uses `tmp_path` and monkeypatching. It will **not write** to the real
`data/local/` or `artifacts/` directories. It does not click CTAs, submit forms,
run Google Analytics, or inspect checkout payment operations.

## Commands (PowerShell, project root)

```powershell
uv run pytest tests/e2e/test_audit_history_export_flow.py -v
uv run pytest -q
```

Expected after Stage 18 history-refresh correction: **282 tests** total, if the
previously confirmed local suite still contains 278 tests and none were removed.

## What this does not certify

1. Visual findings on real JavaScript-heavy landing pages; guarded public browsing disables JS.
2. Safe public deployment of remote browser or Lighthouse jobs; the current opt-in is **local development only**.
3. Real Lighthouse, axe-core or Impeccable execution in the main audit endpoint.
4. Accuracy for a real marketing landing page: that requires manual comparison with observable HTML/URL findings on an authorized test page.
5. Final UX acceptance; Overview, prioritization, coverage, and screenshots are scheduled for refinement after Stage 18.

## Release gate (still pending)

- Validate two authorized marketing landing pages (one with URL campaign parameters; one with navigation to checkout or signup) against observed evidence.
- Resolve or explicitly document any mismatch between report claims and actual execution.
- Test external engines in isolation and decide whether to expose them in the local workflow under a safe, controlled runtime; never mark unrun engines as completed.
- Review SSRF, DNS rebinding, redirects, browser request interception, artifacts and secrets before public deployment.
- Update README and run instructions only once these implementation decisions are established.
- Perform the agreed final visual review of the Streamlit interface.

## Git

Keep this test in its own Stage 18 commit after validating locally:

```powershell
git add tests/e2e/test_audit_history_export_flow.py docs/FINAL_E2E_GATE_STAGE18.md
git commit -m "test(e2e): cover audit history reopening and exports"
```
