"""STAGE36 offline integration check: kernel sandbox + guarded rendering.

Run in the stage36 API Docker image; no Neon, public URLs or credentials.
This does not assert that the Render host/container networking is isolated.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from playwright.sync_api import sync_playwright

from pagecheck.acquisition.browser.egress_guard import launch_guarded_chromium


def main() -> None:
    wrapper = os.environ.get("PAGECHECK_BROWSER_SECCOMP_LAUNCHER", "")
    if not wrapper or not Path(wrapper).is_file():
        raise RuntimeError("Missing STAGE36 Chromium syscall wrapper")
    check = subprocess.run([wrapper, "--self-test"], capture_output=True,
                           text=True, timeout=10, check=True)
    if "STAGE36_SYSCALL_GUARD_SELFTEST_PASSED" not in check.stdout:
        raise RuntimeError("Chromium syscall filter self-test did not pass")
    print(check.stdout.strip())

    with sync_playwright() as playwright:
        browser = launch_guarded_chromium(playwright.chromium)
        try:
            context = browser.new_context(java_script_enabled=False,
                                          service_workers="block", accept_downloads=False)
            try:
                context.route("**/*", lambda route: route.fulfill(
                    status=200, content_type="text/html",
                    body="<html><body>PAGECHECK_SANDBOX_RENDER_OK</body></html>",
                ))
                page = context.new_page()
                page.goto("https://example.org/", wait_until="domcontentloaded", timeout=15000)
                if "PAGECHECK_SANDBOX_RENDER_OK" not in page.content():
                    raise RuntimeError("Sandbox browser did not render an intercepted page")
                print("STAGE36_BROWSER_GUARDED_RENDER_PASSED")
            finally:
                context.close()
        finally:
            browser.close()
    print("STAGE36_BROWSER_KERNEL_SMOKE_PASSED")
    print("RENDER_CONTAINER_EGRESS_ISOLATION_NOT_VERIFIED")


if __name__ == "__main__":
    main()
