# STAGE36 — Chromium syscall guard (Render deployment preparation)

This stage adds an **OS-enforced, per-browser-process** restriction on new
network sockets. It does **not** claim that the complete Render container or
Python backend has outbound network isolation. Arbitrary URL auditing in
production remains **disabled** by default.

## Scope and reason

- The existing Stage35 unreachable proxy is retained.
- An additional native launcher (`deploy/browser_no_net.c`) applies a Linux
  seccomp BPF filter before starting Chromium. The filter permanently denies
  `socket()` except AF_UNIX (needed for Chromium IPC), plus `io_uring_setup()`
  to avoid asynchronous socket creation. It is inherited by Chromium's children.
- This launcher uses stdin/stdout pipes for Playwright control. Browser assets
  continue to be fulfilled by `context.route()` from the Page Check Python
  `PublicHTTPTransport`, which validates and pins public TCP IP destinations.
- Chromium runs with a minimal environment **without** API tokens or Neon
  credentials.
- The executable is built in a separate Docker stage, so the final image does
  not contain C compilers. Builds fail if the seccomp self-test cannot run.
- Without this executable, production Chromium refuses to start. Local Windows
  development keeps the old Stage35 proxy behavior and is unchanged.

## What this does not establish

1. The trusted Python FastAPI process still has network access, including
   legitimate Neon and web requests. Its HTTP fetcher must continue to enforce
   URL, DNS, redirects, limits, TLS and IP pinning.
2. This is a Chromium **process** restriction, not an external network policy,
   a per-container firewall or a guarantee against every kernel/browser escape.
3. Render's service-to-service private network does **not** control its public
   outbound traffic. The Render-hosted workload still needs a deployment
   security review, a verified sandbox boundary and end-to-end testing.
4. The Render Blueprint intentionally remains
   `PAGECHECK_PUBLIC_AUDITS_ENABLED=0` and `PAGECHECK_EGRESS_ISOLATED=0`.
   Do not change these flags on the strength of the Stage36 smoke test alone.
5. This package was prepared from the original committed project snapshot plus
   Stage32–35 patches. Review the Git diff before staging.

## PowerShell: install and validate (repository root)

```powershell
Expand-Archive `
  -LiteralPath "$env:USERPROFILE\Downloads\pagecheck-stage36-chromium-kernel-guard.zip" `
  -DestinationPath . -Force

uv run pytest -q

docker build -f deploy/Dockerfile.api -t pagecheck-api:stage36 .

docker run --rm --entrypoint /usr/local/bin/pagecheck-chromium-sandbox `
  pagecheck-api:stage36 --self-test

docker run --rm `
  -e PAGECHECK_ENV=production `
  -v "${PWD}/scripts/stage36_browser_kernel_smoke.py:/app/stage36_browser_kernel_smoke.py:ro" `
  --entrypoint /app/.venv/bin/python `
  pagecheck-api:stage36 /app/stage36_browser_kernel_smoke.py
```

**Expected** (the browser smoke may fail on a host whose container runtime
prohibits applying seccomp):

```
SECCOMP_IPV4_BLOCKED
SECCOMP_IPV6_BLOCKED
SECCOMP_UNIX_IPC_ALLOWED
STAGE36_SYSCALL_GUARD_SELFTEST_PASSED
STAGE36_BROWSER_GUARDED_RENDER_PASSED
STAGE36_BROWSER_KERNEL_SMOKE_PASSED
RENDER_CONTAINER_EGRESS_ISOLATION_NOT_VERIFIED
```

A failing build/smoke is a **stop condition**, not a reason to disable the
sandbox. Do not set `PAGECHECK_ENV=development` in Render.

## Local commit only — AFTER full tests and the Chromium Docker smoke pass

```powershell
git status --short
git add -- deploy/Dockerfile.api deploy/browser_no_net.c `
  src/pagecheck/acquisition/browser/egress_guard.py `
  scripts/stage36_browser_kernel_smoke.py `
  tests/unit/test_stage36_kernel_browser_sandbox.py `
  docs/STAGE36_KERNEL_BROWSER_SANDBOX.md

git diff --cached --check
git diff --cached --stat
git commit -m "security(browser): enforce kernel socket guard for Chromium"
git status --short
```

No push. A separate Render production security verification is still required
before making user-controlled URL audits public.
