# Page Check — Stage 16D: guarded visual capture in the combined audit

## Scope

Connect the Stage 9–12 Playwright, screenshot annotation, image-quality, and responsive-layout modules to the existing Stage 16C combined HTML/SEO/URL audit. **No new runtime dependency** is introduced.

The main `POST /v1/audits/page` endpoint remains backward compatible. With normal configuration it runs only HTML/SEO/URLs, exactly as in Stage 16C. When the two **local-development-only** opt-ins are enabled, the same request also obtains two guarded, static browser captures (1280px desktop and 390px mobile). These are consolidated in the same report and displayed in its **Screenshots** tab. Failure to launch Chromium or load a viewport does **not** erase the HTML audit; that viewport remains `not_verified`.

## Added/updated modules

- New `src/pagecheck/application/use_cases/collect_public_visuals.py`: launches Chromium, opens separate guarded browser contexts for desktop and mobile, writes evidence under `artifacts/page_audits/<random-id>/<viewport>/`.
- Updated `src/pagecheck/application/use_cases/audit_visual_viewport.py`: treats resources blocked by Page Check's policy as **not verified**, not as proven broken images; draws markers from the remaining actual findings.
- Updated `src/pagecheck/application/use_cases/audit_page_html.py`: accepts an optional visual collector after one HTML fetch and passes the observations to the existing consolidated-report constructor.
- Updated `src/pagecheck/application/use_cases/consolidate_audit.py`: records limitations for static browser mode; `partial` is appropriate even if screenshots exist.
- Updated `src/pagecheck/api/routes/audit.py`: enables visual collection only with an explicit environment flag and a loopback client request; current HTML-only behavior is unchanged by default.
- Updated UI and English presentation: links screenshots when local file paths exist, translates existing visual rule titles, and distinguishes completed, limited, and unrun sources.
- New `tests/unit/test_live_visual_aggregation.py` and `tests/integration/test_visual_overlay_regression.py`.
- New offline demonstration: `scripts/visual_report_fixture_smoke.py`.

## Install in Windows PowerShell

In the `pagecheck` repository, after committing Stage 16C:

```powershell
Expand-Archive -Path "$HOME\Downloads\PageCheck_Etapa16D_Integracao_Visual.zip" -DestinationPath . -Force
uv run pytest tests/unit/test_live_visual_aggregation.py tests/integration/test_visual_overlay_regression.py -v
uv run pytest -q
```

Stage 16C had **235 tests** on the user's machine. This update adds **10**; expected **245**, assuming the same baseline. The smaller reference copy used to validate this ZIP passed **212 tests**.

## Offline screenshot demonstration (no internet)

```powershell
uv run python scripts/visual_report_fixture_smoke.py
```

The script creates:

- `artifacts/page_audits/stage16d_fixture/consolidated_visual_audit.json`
- `artifacts/page_audits/stage16d_fixture/desktop/after_scroll_annotated.png`
- `artifacts/page_audits/stage16d_fixture/mobile/after_scroll_annotated.png`

In Streamlit, expand **Import an existing audit report** and upload that JSON. Both marked screenshots should appear in **Screenshots**, because all files are on the same local machine.

## Test a public page locally

Stop the FastAPI server (`Ctrl+C`) and restart it in the same PowerShell terminal:

```powershell
$env:PAGECHECK_ALLOW_LIVE_FETCH="1"
$env:PAGECHECK_ALLOW_LIVE_BROWSER="1"
uv run uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

In another terminal:

```powershell
uv run streamlit run streamlit_app.py
```

Open `http://localhost:8501`, enter a public URL, niche, content language, goal, and keywords, then click **Audit page**. The **Screenshots** tab will display captured viewports if available. A plain page like `https://example.com` will typically have no drawn issue markers because none were detected. A non-trivial website might not render fully in static mode.

To stop using live browser capture, restart the FastAPI process without `PAGECHECK_ALLOW_LIVE_BROWSER` (or execute `Remove-Item Env:PAGECHECK_ALLOW_LIVE_BROWSER` in the terminal before restarting). Never enable browser capture in a public deployment.

## Security and accuracy limits

- This is **not a production-grade browser sandbox**. Use only in a local test environment with the API bound to loopback. Production deployment requires OS/network isolation and additional hardening.
- JavaScript, Service Workers, downloads, WebSockets, and non-GET requests are disabled/blocked. Browser subresources are acquired only by the previously established guarded Python fetcher. Each viewport has request and byte limits.
- JS-dependent layouts, dynamic checkouts, buttons, form submissions, tracking events, and user journeys **are not tested** by this browser mode. Such checks stay `not_verified`.
- A blocked resource is **not** marked as an origin-site error. Real mobile layout findings are derived from observable geometry only, with false-positive-prone cases flagged for review.
- The visual renderer may fetch the same public document again inside the guarded browser after the initial HTML audit. The HTML/SEO pipeline itself still makes one fetch.
- Screenshot paths are local and are displayed only from the project's `artifacts/` directory. Files remain excluded from Git.
- Lighthouse, axe-core, and Impeccable are **not** executed by the main form in this stage. Their integrations remain available independently for a subsequent step.
