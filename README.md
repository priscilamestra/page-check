# Page Check

**Deterministic landing-page audit with guarded public scanning, JavaScript screenshots, private 24-hour recovery and portable exports.**

Page Check performs deterministic landing-page checks for technical marketing/GTM teams, without generative AI or paid APIs. It reports what was actually verified. It does not measure Google rankings, real analytics conversions, completed checkouts or full WCAG compliance.

## Requirements

- Windows PowerShell or equivalent terminal, Python 3.11+ and `uv`.
- Playwright Chromium installed for optional browser visual inspection.
- For local engine checks, install the pinned `axe-core` and Impeccable dependencies with `npm ci`. The API image packages only the bounded axe script and Impeccable native detector. Lighthouse runs only on a **trusted local fixture**, not arbitrary public URLs.

Install the project's Python dependencies (`uv sync`) and, where applicable, its browser/Node dependencies as described in the linked stage docs. The project must not auto-install CLI packages in the course of an audit.

## Start locally (two VS Code PowerShell terminals)

**Terminal 1 — FastAPI (loopback only):**

```powershell
$env:PAGECHECK_ALLOW_LIVE_FETCH="1"
$env:PAGECHECK_ALLOW_LIVE_BROWSER="1"
$env:PAGECHECK_ALLOW_LOCAL_STATIC_ENGINES="1"
uv run uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

API health: http://127.0.0.1:8000/health

**Terminal 2 — Streamlit:**

```powershell
uv run streamlit run streamlit_app.py --server.address 127.0.0.1 --server.port 8501
```

UI: http://localhost:8501

These opt-in environment variables are **strictly for local development**. Keep the servers bound to `127.0.0.1`. Do not expose this configuration through a public server, reverse proxy, or cloud deployment. Stop with `Ctrl+C` in both terminals.

Run tests:

```powershell
uv run pytest -q
```

## What an audit contains

Enter a public URL, niche, content language, page goal and target keyword tags, then press **Audit page**. The report can include:

- Technical HTML SEO (title, description, headings, canonical, alt text) plus separate content/keyword guidance. A score of 100/100 refers **only to eligible scored technical checks**.
- URL/UTM journey, structural links/CTAs, form and analytics-tag presence (without visiting unsafe destinations, sending forms, or claiming events reached analytics tools).
- Desktop/mobile evidence with JavaScript rendered through a guarded GET-only path. POST, WebSocket, downloads, service workers and direct browser sockets stay blocked. Oversized pages may provide only first-viewport partial evidence.
- Optional static HTML accessibility checks (axe-core) and design heuristics (Impeccable). Neither is a complete live-site audit.
- Local SQLite history in development; production uses one opaque browser token for private PostgreSQL recovery for up to 24 hours. JSON/CSV/HTML+PNG ZIP exports remain available.

`Not verified` means insufficient evidence or a check not performed; it is not a defect. `Needs review` means a human should confirm an observation. Lighthouse on a public URL remains `Not verified`. Check **Overview → Audit sources** and **Screenshots** for recorded reasons when a source did not finish.

## Project structure

| Area | Location |
|---|---|
| API and request validation | `src/pagecheck/api/` |
| Audit orchestration | `src/pagecheck/application/use_cases/` |
| Guarded HTTP / browser acquisition | `src/pagecheck/acquisition/` |
| Rule modules | `src/pagecheck/audits/` |
| External engine adapters | `src/pagecheck/integrations/` |
| Streamlit UI | `src/pagecheck/ui/` |
| Consolidation and exports | `src/pagecheck/reporting/` |
| SQLite local audit history | `src/pagecheck/persistence/sqlite/` |
| Tests | `tests/` |
| Stage documentation | `docs/` |

## Security and limitations

Production scanning is fail-closed. It requires the Stage 43 seccomp worker, AF_UNIX fetch broker, private service key, request admission limits and explicit deployment flags. The checked-in `render.yaml` keeps those flags disabled until the image and hosted isolation smoke tests pass. See [Stage 43 public audits](docs/STAGE43_RENDER_FREE_PUBLIC_AUDITS.md).


- Public-host validation, DNS/IP pinning, bounded GETs and process-level socket denial protect the scanner path. This is process isolation, not a claim of a container-wide firewall.
- Page JavaScript renders only through intercepted requests. Interactive clicks and form submissions are never executed.
- axe-core and Impeccable analyze sanitized, bounded HTML in the isolated worker. Lighthouse launches its own network-capable Chrome and remains deliberately excluded from arbitrary public targets.
- Output may contain URLs, HTML evidence or screenshot metadata. Local history and exported reports should be handled as private project data. `data/local/` and `artifacts/` are excluded from Git.
- No paid APIs, private-data collection, real lead submissions, behavioral heatmaps, or automatic production deployment.

## Further documentation

- [Stage 18 coverage and failure diagnostics](docs/STAGE18_COVERAGE_DIAGNOSTICS.md)
- [Stage 18 safe static engines](docs/STATIC_ENGINES_STAGE18.md)
- [Stage 18 E2E offline test](docs/FINAL_E2E_GATE_STAGE18.md)
- [Stage 17 local history and exports](docs/HISTORY_STAGE17.md)
- [Visual static-browser integration](docs/UI_STAGE16D.md)
- [Architecture](docs/ARCHITECTURE.md) · [API contract](docs/API_CONTRACT.md) · [PRD](docs/PRD.md)

**Known limitation:** Lighthouse remains `not_verified` for public URLs because its separate Chrome process is not connected to the guarded fetch broker. Hosted release still requires the documented 512 MB and Render isolation smoke tests before enabling public audit flags.
