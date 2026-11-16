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
from pagecheck.acquisition.browser.visual_probe import inspect_visible_images
from pagecheck.acquisition.browser.visual_hierarchy import inspect_heading_hierarchy
from pagecheck.reporting.annotations.findings import (build_image_findings,
    build_capture_image_warnings)
from pagecheck.reporting.annotations.overlay import annotate_screenshot, write_annotation_manifest
from pagecheck.common.security.url_validation import validate_public_url

PROJECT_ROOT = Path(__file__).resolve().parents[4]
VIEWPORTS = {"desktop": (1280, 720), "mobile": (390, 720)}
MAX_DOCUMENT_HEIGHT = 8000


def capture_with_browser(
    browser: Browser, *, url: str, output_dir: Path,
    fetch_resource: Callable[..., Any] = fetch_public_resource,
    include_rendering_hints: bool = False,
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
            if document_height < 1:
                errors[viewport] = "Document height could not be measured."
                continue
            if document_height > MAX_DOCUMENT_HEIGHT:
                # Do not try a full-page screenshot on oversized pages. Inspect
                # ONLY image elements intersecting the first viewport and mark
                # failures only after excluding requests blocked by our policy.
                folder = output_dir / viewport
                folder.mkdir(parents=True, exist_ok=True)
                screenshot = folder / "initial_viewport.png"
                page.screenshot(path=str(screenshot), full_page=False,
                                animations="disabled", timeout=10000)
                # Image inspection is additional evidence, not a prerequisite
                # for the safe initial-viewport screenshot. In particular,
                # controlled pages or restricted documents may not support the
                # DOM image probe at all; preserve the captured viewport and
                # mark image diagnostics unavailable rather than failing it.
                image_probe_error = None
                try:
                    images = inspect_visible_images(page)
                except Exception as exc:
                    images = []
                    image_probe_error = type(exc).__name__
                blocked = {row["url"] for row in getattr(network, "blocked", [])}
                for img in images:
                    if img.get("src") in blocked:
                        img["status"] = "not_verified"
                findings = build_image_findings({"images": images})
                if include_rendering_hints:
                    findings += build_capture_image_warnings({"images": images})
                try:
                    hierarchy = inspect_heading_hierarchy(page)
                except (TypeError, ValueError, AttributeError):
                    hierarchy = {"status": "not_verified", "headings_checked": 0, "findings": []}
                findings += hierarchy["findings"]
                for finding in findings[:]:
                    if finding.get("category") != "images" or finding.get("status") != "failed":
                        continue
                    finding["title"] = "Imagem não carregou na área visível"
                    finding["description"] = (
                        "A imagem visível não foi decodificada neste navegador "
                        "com JavaScript desativado. Verifique a URL e o arquivo."
                    )
                screenshot_paths = {"initial": str(screenshot)}
                if findings:
                    annotated_path = folder / "initial_viewport_annotated.png"
                    annotated = annotate_screenshot(
                        screenshot_path=screenshot,
                        output_path=annotated_path,
                        findings=findings,
                        viewport_width=width,
                        page_height=height,
                    )
                    screenshot_paths["annotated"] = str(annotated_path)
                    manifest = folder / "annotations.json"
                    write_annotation_manifest({**annotated, "findings": findings}, manifest)
                results[viewport] = {
                    "viewport": viewport,
                    "screenshots": screenshot_paths,
                    "findings": findings,
                    "design_review": {"status": hierarchy["status"],
                                      "headings_checked": hierarchy["headings_checked"],
                                      "scope": "first viewport"},
                    "scroll_complete": False,
                    "geometry": {"document_height": document_height, "truncated": True},
                    "images": {
                        "total": len(images),
                        "broken": sum(img["status"] == "broken" for img in images),
                        "not_verified": sum(img["status"] == "not_verified" for img in images),
                    },
                    "limitations": [
                        f"Page height exceeds the safe {MAX_DOCUMENT_HEIGHT}px full-page limit. "
                        + ("Image checks were unavailable; only the first viewport was captured without annotations. "
                           if image_probe_error else
                           "Only visible images in the first viewport were checked. ")
                        + "The rest of the page and layout were not verified.",
                        "JavaScript is disabled; JS-dependent content was not verified.",
                        *([f"Initial-viewport image inspection was not verified ({image_probe_error})."]
                          if image_probe_error else []),
                    ],
                    "network": {
                        "requested": getattr(network, "requested", 0),
                        "delivered": getattr(network, "delivered", 0),
                        "blocked_count": len(blocked),
                    },
                }
                continue
            observation = audit_visual_viewport(
                page, output_dir=output_dir / viewport,
                blocked_urls=lambda: {row["url"] for row in network.blocked},
                include_rendering_hints=include_rendering_hints,
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
        "status": "partial" if (errors or len(results) != len(VIEWPORTS)
                              or any(not item.get("scroll_complete", True)
                                     for item in results.values())) else "captured",
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
            return capture_with_browser(browser, url=url, output_dir=directory,
                                        include_rendering_hints=True)
        finally:
            browser.close()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            return capture_with_browser(browser, url=url, output_dir=directory,
                                        include_rendering_hints=True)
        finally:
            browser.close()
