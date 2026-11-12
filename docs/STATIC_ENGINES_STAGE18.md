# Stage 18 — local opt-in static external engines

## Scope

This patch connects **axe-core** and the locally installed **Impeccable CLI** to the existing **Audit page** flow for *sanitized, static HTML only*. **Lighthouse remains explicitly `not_verified` on public URLs** because its Chrome network traffic bypasses Page Check's pinned safe HTTP client. Use the existing trusted fixture script to exercise Lighthouse (`--live-local`) without providing arbitrary input.

This is a conservative dev-only diagnostic, **not a network sandbox**. Never expose the flag in a public deployment or enable it for remote API clients.

## How to run locally on Windows PowerShell

Install the existing Node dependencies if necessary: `npm install`.

Terminal 1 (FastAPI only on loopback):

```powershell
$env:PAGECHECK_ALLOW_LIVE_FETCH="1"
$env:PAGECHECK_ALLOW_LOCAL_STATIC_ENGINES="1"
$env:PAGECHECK_ALLOW_LIVE_BROWSER="1" # optional, existing safe static screenshots
uv run uvicorn main:app --host 127.0.0.1 --port 8000
```

Terminal 2:

```powershell
uv run streamlit run streamlit_app.py --server.address 127.0.0.1
```

Press **Audit page** for a public URL. The server fetches HTML once, checks URLs and SEO, then passes **sanitized HTML** (no scripts, network URLs, styles or embedded content) to the extra analyzers. Both analyzers use the already fetched HTML, not the public URL. The axe browser blocks *all* HTTP requests; the Impeccable detector receives a temporary local HTML file and runs under a 40-second timeout.

The detailed report records source statuses. `completed` means the supported subset ran, **not** that the site passed or meets WCAG requirements. `not_verified` means the tool did not run or could not interpret the output. Lighthouse scores stay `null` in live public audits.

## Tests

```powershell
uv run pytest tests/unit/test_static_external_engines.py tests/unit/test_static_external_api.py -v
uv run pytest -q
```

## Limitations, by design

- **axe-core:** static DOM semantic checks only. No live JavaScript, CSS-dependent contrast, checkout, or interaction assessment. Runtime accessibility and complete WCAG compliance remain unverified.
- **Impeccable:** heuristics on sanitized markup, not original layout or CSS. A detector CLI schema change may leave it `not_verified`.
- **Lighthouse:** not run against external websites from this mode. The supplied `scripts/external_engines_fixture_smoke.py --live-local` is still the separate, trusted localhost exercise and its scores are for the fixture only.
- No third-party account access, paid API, forms submission, endpoint penetration testing or user tracking.
- Enabled only for loopback requests and with the explicit flag. This does not replace OS network isolation for deployed browsing.

To disable after use: stop FastAPI, then `Remove-Item Env:PAGECHECK_ALLOW_LOCAL_STATIC_ENGINES -ErrorAction SilentlyContinue` in that terminal.
