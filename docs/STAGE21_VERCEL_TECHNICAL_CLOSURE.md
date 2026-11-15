# Stage 21 — Vercel technical closure (read before any deployment)

## Decision: NO direct public deploy yet

The production safeguards from Stage 20 deliberately disable live URL collection and unauthenticated SQLite history outside development. Do **not** bypass them to make a demo appear to work.

### Verified platform constraints (November 2026)

- **FastAPI:** officially supported as Python deployment / Vercel Function. The Python runtime is GA.
  https://vercel.com/docs/frameworks/backend/fastapi
  https://vercel.com/changelog/python-on-vercel-is-now-generally-available
- **Streamlit:** needs persistent server/WebSocket interaction. Vercel Functions, including functions packaged in containers, cannot serve as WebSocket servers. A successful build does not imply a working Streamlit UI.
  https://vercel.com/docs/limits
  https://vercel.com/changelog/deploy-a-container-from-a-plain-dockerfile
- **SQLite and screenshot files:** Vercel Functions have read-only deployment files and disposable `/tmp` scratch space (up to 500 MB), not durable app history.
  https://vercel.com/docs/functions/runtimes
- **Browser audits:** do not enable arbitrary outbound Chromium browsing from a public request handler. The existing local HTTPX validation is not enough for a separate Chrome process.

## Vercel architecture that preserves Page Check's product goals

1. **Frontend:** once the remaining design edits are approved, build a Vercel-compatible web UI. Preserve the existing decision model, inputs, reports, SEO rules and export formats. Do not merely package the current Streamlit server in a Dockerfile and assume WebSockets work.
2. **FastAPI:** deploy only endpoints that are safe as bounded, request-driven functions. Current production audit routes return 503 by design until an isolated scanner is introduced.
3. **Isolated scanning execution:** queue jobs for a constrained worker/browser environment with egress restrictions, re-resolved DNS and redirect policy, timeouts, CPU/memory limits and concurrency caps. Evaluate platform services/costs before implementing.
4. **No login:** public MVP can return reports immediately and allow browser-side downloads. Disable shared history by default. Do not expose a shared report index or assume an unguessable ID substitutes for authorization. If persistent history becomes necessary, define durable storage and access policy first.
5. **Privacy and usage:** rate limiting; URL retention and screenshot retention limits; deletion mechanisms; no private IPs or intranet fetch; no form submissions; abuse and denial-of-service safeguards.
6. **End-to-end verification:** test multiple users, refresh, export, safe link behavior, throttling, blocked IPs, redirects, and production deployment settings before releasing publicly.

**Do not add a `vercel.json` that pretends this entire project can already run publicly.** A frontend entrypoint and isolated scanner architecture must exist first.

## Diagnose installed Impeccable without leaking page content

Run locally from the project root:

```powershell
uv run python scripts/impeccable_contract_probe.py
```

The script invokes the **locally installed executable only**, with a synthetic HTML fixture, and prints safe schema metadata. It neither fetches public URLs nor downloads tools via `npx`.

Optional, to inspect a **known local HTML file** that may trigger the problematic shape:

```powershell
uv run python scripts/impeccable_contract_probe.py --html-file .\artifacts\my-trusted-snapshot.html
```

Never pass a URL; the probe does not make HTTP requests. The output prints only field names and counts, not HTML, paths, rule message values, or selectors. If the result is `adapter_compatible: false`, preserve `not_verified` until the actual schema is analyzed and the adapter is fixed with version-specific tests.

## Predeployment blocker report

```powershell
uv run python scripts/vercel_deploy_preflight.py
uv run python scripts/vercel_deploy_preflight.py --strict
```

The first produces a status report without deploying. The second intentionally exits `2` while any public deployment requirement is missing (useful for CI). This is a product-safety gate, not a deploy command.

## Release sequence

1. Validate Stage 21 tests and the Impeccable probe on the real Windows project.
2. Finish any unresolved detector schema mismatch, retaining explicit `not_verified` if it cannot run.
3. User reviews final UI details; only then port that interface to a Vercel-compatible frontend.
4. Implement isolated scan workers and storage/privacy decisions.
5. Execute security and end-to-end tests in a non-public preview.
6. Publish on Vercel after *all* preflight requirements pass.
