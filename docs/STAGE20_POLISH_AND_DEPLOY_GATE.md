# Stage 20 — Last UI polish and secure deployment gate

## Intent

Keep the Stage 19 UX direction and improve the few remaining sources of friction without changing the audit/scoring models or SQLite structure.

## UI changes

- **URLs & parameters:** the checks table now fits the filtered row count. One result no longer creates a large mostly-empty grid. Hundreds of records scroll within a bounded table.
- **Issues / Teams:** the same reusable compact-height calculation applies.
- **Overview:** top findings and screenshots remain visible; detailed source cards and the breakdown of unverified checks are accessible in collapsed, labeled expanders. The actual seven-source composition stays visible and numeric.
- **Data:** exports and raw JSON are unchanged.

## Impeccable diagnostics (not a compatibility claim)

The real HubSpot audit reported unrecognized Impeccable output. The adapter still refuses records without stable rule IDs. The error now states the **1-based finding number and the field names only**, without printing original HTML, rule-message values, or CLI stdout. It does not pretend the detector completed and does not fabricate findings. Confirm the real-world CLI schema on a fresh locally opted-in audit before claiming this engine is fixed.

## Public deployment is BLOCKED until isolation is designed

**Current Page Check is a local-only MVP.** Switching `PAGECHECK_ENV=production` (or any unrecognized environment) now fails closed: live fetch routes return 503 even if `PAGECHECK_ALLOW_LIVE_FETCH=1`, and unauthenticated local history routes return 503. The health endpoint remains available. Development tools are hidden outside recognized local modes. This is a safety gate, **not** a method to ship a functioning public scanner.

A later public deployment needs, at minimum:

1. A chosen hosting and threat model (who may submit URLs, how many concurrent scans, data retention);
2. Network egress restrictions and a dedicated sandbox for Chromium / subprocesses;
3. Rate limits, per-job time/CPU/memory ceilings, queueing and controlled concurrency;
4. Independent request authorization between the UI and API, and a safe history policy without exposing local reports to other users;
5. Privacy/data-retention/export review and tests against redirect, DNS-rebinding and non-HTTP schemes;
6. A separate integration-test pass using the actual installed Impeccable version.

There is deliberately **no login** in this local version. Do not infer access control from the top-right Tools menu.

## Local validation

```powershell
uv run pytest tests/unit/test_ui_polish_stage20.py tests/unit/test_production_gate_stage20.py tests/unit/test_impeccable_diagnostics_stage20.py -v
uv run pytest -q
```

Reuse a saved HubSpot report. Verify the URL table is compact with one match, that seven source cards are available under an expander, and that screenshots remain visible. A new local audit is needed to exercise the improved Impeccable schema explanation.

Do not make a Git commit until the complete test suite passes on the local checkout.
