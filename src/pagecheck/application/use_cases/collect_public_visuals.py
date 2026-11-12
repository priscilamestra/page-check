"""Optional local-only public-page visual capture using existing guarded Playwright routes.

This is a conservative renderer: JavaScript is disabled, browser requests are
intercepted by the Python IP-pinned HTTP transport, and only GET HTML/CSS/images/
fonts are allowed. It is NOT a network sandbox for publicly deployed auditing.
"""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any
from uuid import uuid4

from playwright.sync_api import Browser, sync_playwright

from pagecheck.acquisition.browser.public_navigation import (
    fetch_public_resource, install_guarded_routes,
)
from pagecheck.application.use_cases.audit_visual_viewport import audit_visual_viewport
from pagecheck.common.security.url_validation import validate_public_url

PROJECT_ROOT = Path(__file__).resolve().parents[4]
VIEWPORTS = {"desktop": (1280, 720), "mobile": (390, 720)}
MAX_DOCUMENT_HEIGHT = 8000


def capture_with_browser(
    browser: Browser, *, url: str, output_dir: Path,
    fetch_resource: Callable[..., Any] = fetch_public_resource,
) -> dict[str, Any]:
    """Capture two independent viewports without clicks, POST, or JavaScript.

    Network failures leave the individual viewport unverified. This function
    never turns blocked assets into confirmed broken images.
    """
    url = validate_public_url(url)
    results: dict[str, dict[str, Any]] = {}
    errors: dict[str, str] = {}
    for viewport, (width, height) in VIEWPORTS.items():
        context = None
        try:
            context = browser.new_context(
                viewport={"width": width, "height": height},
                device_scale_factor=1,
                java_script_enabled=False,
                service_workers="block",
                accept_downloads=False,
                permissions=[],
            )
            network = install_guarded_routes(
                context, fetch_resource=fetch_resource,
                max_requests=35, max_total_bytes=8_000_000,
            )
            page = context.new_page()
            response = page.goto(url, wait_until="domcontentloaded", timeout=15000)
            if response is None or not response.ok:
                errors[viewport] = "The page could not be loaded in the guarded browser."
                continue
            document_height = int(page.evaluate(
                "() => Math.max(document.body.scrollHeight, document.documentElement.scrollHeight)"
            ))
            if document_height < 1 or document_height > MAX_DOCUMENT_HEIGHT:
                errors[viewport] = "The document exceeds the safe visual capture height."
                continue
            observation = audit_visual_viewport(
                page, output_dir=output_dir / viewport,
                blocked_urls=lambda: {row["url"] for row in network.blocked},
            )
            observation["limitations"] = [
                "JavaScript is disabled: interactive widgets, client-side navigation "
                "and JS-only content have not been tested."
            ]
            if network.blocked:
                observation["limitations"].append(
                    f"{len(network.blocked)} network requests were blocked or could not be fetched; "
                    "blocked assets are not confirmed page defects."
                )
            observation["network"] = {
                "requested": network.requested,
                "delivered": network.delivered,
                "blocked_count": len(network.blocked),
            }
            results[viewport] = observation
        except Exception as exc:
            # A visual failure should not erase a valid HTML / SEO audit.
            errors[viewport] = f"Visual inspection unavailable ({type(exc).__name__})."
        finally:
            if context is not None:
                context.close()
    return {
        "visuals": results,
        "status": "partial" if errors or len(results) != len(VIEWPORTS) else "captured",
        "errors": errors,
        "mode": "guarded_static_no_javascript",
    }


def collect_public_visuals(
    url: str, *, output_base: Path | None = None,
    browser_launcher: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Local-only collector, producing files inside ``artifacts/page_audits``.

    ``browser_launcher`` allows offline tests to supply a controlled Chromium.
    Public deployment MUST NOT enable this function without OS-level isolation.
    """
    url = validate_public_url(url)
    base = output_base if output_base is not None else PROJECT_ROOT / "artifacts" / "page_audits"
    directory = Path(base) / uuid4().hex
    directory.mkdir(parents=True, exist_ok=False)
    if browser_launcher is not None:
        browser = browser_launcher()
        try:
            return capture_with_browser(browser, url=url, output_dir=directory)
        finally:
            browser.close()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            return capture_with_browser(browser, url=url, output_dir=directory)
        finally:
            browser.close()
