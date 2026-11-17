# STAGE35 — Browser outbound guard (defense in depth)

## What changed

- The default `collect_public_visuals()` Chromium process is launched with an intentionally unreachable loopback HTTP proxy (`127.0.0.1:9`).
- Requests already intercepted with Playwright `context.route()` may still be **fulfilled** from the existing Python `PublicHTTPTransport`, which checks public IPs and pins the connection to a validated numerical address.
- JavaScript, service workers and downloads remain disabled in the capture contexts.
- The actual public audit feature remains **disabled** on Render by default. This change does **not** turn it on.

## What is and is not validated

- `uv run pytest -q` covers the browser launch configuration, its use in the collector, and fail-closed Render flags.
- Docker smoke test starts a local HTTP service inside the API container and proves a direct Chromium visit cannot reach it, while a Playwright-fulfilled request works.
- **It does not prove OS-level isolation** of all Chromium processes, native sockets, DNS requests, or other components from internal IPs or Render metadata services.
- A Render **private API** protects against public inbound traffic; it does not restrict outbound network access.

**Do not set `PAGECHECK_EGRESS_ISOLATED=1` merely because this smoke test passes.** Before a production release with user-controlled arbitrary URLs, a separate sandbox or firewall enforcement boundary must be deployed and independently tested, as must admission limits and a true end-to-end audit.

## Commands (Windows PowerShell, repo root)

```powershell
uv run pytest -q

docker build -f deploy/Dockerfile.api -t pagecheck-api:stage35 .

docker run --rm --entrypoint python pagecheck-api:stage35 \
    -m playwright --version
```

Windows PowerShell uses backticks for multiline commands. To run the browser smoke test, the script must be copied into the container image. The repository Dockerfile does not currently copy this script; for a one-off local validation use a temporary container with a read-only mount of the script (rather than modifying production images):

```powershell
docker run --rm `
  -v "${PWD}/scripts/stage35_browser_network_smoke.py:/app/stage35_browser_network_smoke.py:ro" `
  --entrypoint /app/.venv/bin/python pagecheck-api:stage35 `
  /app/stage35_browser_network_smoke.py
```

Expected: `BROWSER_DIRECT_LOOPBACK_BLOCKED`, `GUARDED_ROUTE_FULFILL_OK`, `STAGE35_BROWSER_PROXY_SMOKE_PASSED`. This is an offline diagnostic, not a proof of production isolation.

## Local Git only

```powershell
git add -- src/pagecheck/acquisition/browser/egress_guard.py src/pagecheck/application/use_cases/collect_public_visuals.py scripts/stage35_browser_network_smoke.py tests/unit/test_stage35_browser_egress.py docs/STAGE35_BROWSER_EGRESS_GUARD.md
git diff --cached --check
git commit -m "security(browser): constrain native Chromium egress and add smoke checks"
git status --short
```
