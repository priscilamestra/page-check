"""Guarded public-page visual capture using brokered Playwright requests.

Page JavaScript may render, but every HTTP(S) request remains an intercepted,
validated, bounded GET. POST, WebSocket, service workers, downloads, browser
credentials and direct internet sockets remain blocked.
"""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any
from uuid import uuid4

from playwright.sync_api import Browser, sync_playwright

from pagecheck.acquisition.browser.egress_guard import launch_guarded_chromium
from pagecheck.acquisition.browser.layout_probe import collect_layout_observations
from pagecheck.acquisition.browser.public_navigation import (
    fetch_public_resource,
    install_guarded_routes,
)
from pagecheck.acquisition.browser.visual_hierarchy import (
    inspect_heading_hierarchy,
    make_design_review,
)
from pagecheck.acquisition.browser.visual_probe import inspect_visible_images
from pagecheck.application.use_cases.audit_visual_viewport import audit_visual_viewport
from pagecheck.audits.layout.rules import build_layout_findings
from pagecheck.common.security.url_validation import validate_public_url
from pagecheck.reporting.annotations.findings import (
    build_capture_image_warnings,
    build_image_findings,
)
from pagecheck.reporting.annotations.overlay import (
    annotate_screenshot,
    link_marker_numbers,
    write_annotation_manifest,
)

PROJECT_ROOT = Path(__file__).resolve().parents[4]
VIEWPORTS = {"desktop": (1280, 720), "mobile": (390, 720)}
MAX_DOCUMENT_HEIGHT = 8000


def capture_with_browser(
    browser: Browser, *, url: str, output_dir: Path,
    fetch_resource: Callable[..., Any] = fetch_public_resource,
    include_rendering_hints: bool = False,
) -> dict[str, Any]:
    """Capture two independent viewports without clicks, POST, or direct network.

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
                java_script_enabled=True,
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
            # Let bounded async rendering settle without waiting indefinitely for
            # analytics, polling, or other background activity.
            settle = getattr(page, "wait_for_timeout", None)
            if callable(settle):
                settle(750)
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
                except Exception as exc:  # noqa: BLE001 - keep the captured viewport.
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
                # The screenshot is intentionally limited to the first screen,
                # but geometry can still be inspected across the rendered DOM.
                geometry_checked = False
                geometry_truncated = False
                layout_findings = []
                try:
                    layout = collect_layout_observations(page)
                    geometry_checked = (isinstance(layout, dict) and
                                        isinstance(layout.get("viewport_width"), (int, float)) and
                                        isinstance(layout.get("document_width"), (int, float)))
                    if geometry_checked:
                        layout_findings = build_layout_findings(layout)
                        geometry_truncated = layout.get("truncated") is True
                except (TypeError, ValueError, AttributeError):
                    pass
                findings.extend(layout_findings)
                for finding in findings[:]:
                    if finding.get("category") != "images" or finding.get("status") != "failed":
                        continue
                    finding["title"] = "Imagem não carregou na área visível"
                    finding["description"] = (
                        "A imagem visível não foi decodificada neste navegador "
                        "guardado. Verifique a URL, o arquivo e o carregamento dinâmico."
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
                    link_marker_numbers(findings, annotated)
                    screenshot_paths["annotated"] = str(annotated_path)
                    manifest = folder / "annotations.json"
                    write_annotation_manifest({**annotated, "findings": findings}, manifest)
                results[viewport] = {
                    "viewport": viewport,
                    "screenshots": screenshot_paths,
                    "findings": findings,
                    "design_review": make_design_review(
                        hierarchy, layout_findings=layout_findings,
                        geometry_checked=geometry_checked,
                        geometry_truncated=geometry_truncated,
                        screenshot_scope="initial_viewport",
                    ),
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
                        (
                            "JavaScript rendered under the guarded GET-only network budget; "
                            "interactive actions were not executed."
                        ),
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
                blocked_urls=lambda network=network: {
                    row["url"] for row in network.blocked
                },
                include_rendering_hints=include_rendering_hints,
            )
            observation["limitations"] = [
                (
                    "JavaScript rendered under the guarded GET-only network budget; clicks, "
                    "form submissions, WebSockets and client-side actions were not tested."
                )
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
        except Exception as exc:  # noqa: BLE001 - one viewport must not erase the other.
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
        "mode": "guarded_javascript_get_only",
    }


def collect_public_visuals(
    url: str, *, output_base: Path | None = None,
    browser_launcher: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Collector producing files inside ``artifacts/page_audits``.

    ``browser_launcher`` allows offline tests to supply a controlled Chromium.
    Production still requires the Stage 43 OS-level worker isolation.
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
        browser = launch_guarded_chromium(playwright.chromium)
        try:
            return capture_with_browser(browser, url=url, output_dir=directory,
                                        include_rendering_hints=True)
        finally:
            browser.close()
