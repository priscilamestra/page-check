# Stage 18 — truthful coverage and guarded screenshot fallback

## Why this patch exists

A live commercial-page audit returned a technical SEO score of 100/100, 246 `not_verified` checks, no desktop/mobile screenshots and no confirmed Impeccable result. This is **not evidence** that the commercial page passed all checks or that the visual engine failed because of one particular site feature.

The source report already records per-viewport messages in `visual_capture.errors` and detector explanations in `engine_limitations`. Previously, Streamlit mostly hid these behind JSON or generic warnings. This patch displays them directly, retains the underlying report schema, and includes a safe limited capture for pages exceeding the existing 8,000px full-page limit.

## Changed behavior

1. **Overview:** source-by-source statuses (HTML SEO, conversion, desktop, mobile, axe-core, Impeccable, Lighthouse) with recorded reasons. No assumption that `not_verified` is an issue; the KPI now clarifies that these are checks without sufficient evidence.
2. **SEO score:** explicitly labelled as the score for eligible technical rules, independent of content guidance, visual diagnostics and external engines. A 100/100 does not mean complete audit coverage.
3. **By-area counts:** a numeric table supplements the existing graph, including `not_verified` and `not_applicable`. No tooltip is required to read quantities. The definitive visual redesign remains a separate step.
4. **Screenshots:** each viewport shows its own status and any recorded reason; if no reason exists, the interface says so instead of inventing one. Previously saved history reports can show these details without rerunning.
5. **Long pages:** if the static Playwright document height exceeds 8,000px, **do not** take a full-page screenshot or run full layout checks. Save only a 1280x720 or 390x720 first-viewport PNG with `full_page=False`, mark the viewport `partial`, and explicitly state that there are no annotations or full-page findings. Do not relax network, height, download, request, or JavaScript restrictions.
6. **Export/history:** first-viewport-only PNGs are visible in Streamlit, copied by the existing SQLite history implementation (which already supports the `initial` key), and included in ZIP exports. Paths remain constrained to `artifacts/` and PNGs.
7. **CLI diagnostics:** subprocess stdout is decoded as UTF-8; nonzero exits, timeouts and invalid JSON yield short English reasons without exposing stderr or stdout.

## What has NOT been proven or changed

- We have **not** determined the original HubSpot viewport failure reason from screenshots alone. The next opening of that saved audit should reveal whether the report contains a recorded reason. If missing, rerun once with the patch installed and record the new result.
- Impeccable might be missing, incompatible, return a nonzero exit, time out, or produce an unexpected output schema. The patch **reports** the relevant category; it does not automatically install or repair a CLI.
- Lighthouse is still unavailable for arbitrary public URLs. There is no trustworthy result to show for it.
- Huge pages are not marked fully audited. Static browser JavaScript remains disabled.
- The full Overview/screenshot UX redesign, plus robust production network sandboxing, remain separate. **Do not deploy this as a public arbitrary-URL scanning service**.

## Apply on Windows (PowerShell)

Stop the FastAPI/Streamlit terminals, unzip the supplied ZIP into the project root, then run:

```powershell
uv run pytest tests/unit/test_coverage_diagnostics_stage18.py tests/unit/test_long_page_fallback_stage18.py -v
uv run pytest -q
```

Restart the local servers (each in its own terminal) using the established `PAGECHECK_ALLOW_*` dev-only flags. Reopen the saved commercial audit from **Saved audits · local history**. Inspect the new **Audit sources** area in **Overview** and **Screenshots**. Reading an existing report does **not** rerun collection. For a fresh test, use **Audit page** only when you want to compare current behavior.

## Technical/security review notes

- The guarded visual browser still proxies GET HTML/CSS/images/fonts through the existing pinned public-IP transport, with request and byte limits; it does not execute page JavaScript or allow form submission.
- The first-viewport fallback writes one PNG per viewport and does not call layout/annotation analyzers on oversized pages.
- The external static engines receive stripped, bounded HTML without original scripts/styles/URLs. This is a development-only risk reduction, not a hardened sandbox.
- CLI errors exposed in the dashboard are categorical. No exception tracebacks, secrets, arbitrary stderr, or sanitized HTML payloads are printed into the new status panels.
- Existing persisted reports, API source states, SEO scoring rules, database schema, and file paths are left intact.
- Remaining for public deployment: isolated network/browser runtime, authentication/rate limiting, resource quotas, review of local history API access and frontend security. Local loopback flags are not production controls.
