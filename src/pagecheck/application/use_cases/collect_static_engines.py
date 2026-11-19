"""Opt-in static HTML checks using locally installed tools.

No external engine receives a live URL. This module operates only on a
sanitized, bounded *snapshot* of HTML already fetched through safe_transport.
Lighthouse remains unverified because its Chrome bypasses the pinned transport.
Do not enable this in a public deployment without a dedicated sandbox.
"""
from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from bs4 import BeautifulSoup

from pagecheck.application.use_cases.external_engines import combine_engines
from pagecheck.common.security.url_validation import validate_public_url
from pagecheck.integrations.axe.adapter import normalize_axe
from pagecheck.integrations.cli_runner import local_binary, run_local_json_command
from pagecheck.integrations.engine_result import unavailable

# Both supported runtimes keep node_modules next to their project virtualenv.
ROOT = Path(sys.prefix).resolve().parent
MAX_HTML_BYTES = 1_000_000
# Static checks only: anything executable, loadable, or layout-specific is
# stripped before a JS-enabled offline browser is used for axe-core.
UNSAFE_TAGS = {
    "script", "style", "iframe", "frame", "frameset", "object", "embed",
    "link", "base", "meta", "svg", "math", "audio", "video", "source",
    "track", "portal", "template", "noscript", "applet", "canvas",
}
SAFE_ATTRIBUTES = {
    "id", "class", "lang", "dir", "role", "title", "alt", "for", "type",
    "name", "value", "placeholder", "required", "disabled", "checked",
    "readonly", "multiple", "tabindex", "autocomplete", "scope", "colspan",
    "rowspan", "selected", "hidden", "aria-label", "aria-labelledby",
    "aria-describedby", "aria-hidden", "aria-required", "aria-expanded",
    "aria-controls", "aria-live", "aria-current", "aria-invalid",
}
# No visual contrast or runtime behaviour claims. These rules examine only
# semantic HTML and accessible names in the static snapshot.
STATIC_AXE_RULES = (
    "image-alt", "label", "link-name", "button-name", "document-title",
    "html-has-lang", "aria-valid-attr",
)


def sanitize_static_html(html: str) -> str:
    """Preserve semantic markup while removing scripts and all network URLs."""
    if not isinstance(html, str):
        raise TypeError("HTML must be text.")
    if len(html.encode("utf-8")) > MAX_HTML_BYTES:
        raise ValueError("HTML snapshot exceeds the local engine limit.")
    soup = BeautifulSoup(html, "html.parser")
    for tag in list(soup.find_all(True)):
        if tag.name is None or tag.attrs is None:  # Parent may already have been decomposed.
            continue
        if tag.name in UNSAFE_TAGS:
            tag.decompose()
            continue
        for attribute in list(tag.attrs):
            if attribute.lower() not in SAFE_ATTRIBUTES and not attribute.startswith("aria-"):
                del tag.attrs[attribute]
        # Keep img semantics without allowing any external resources.
        if tag.name == "img":
            tag["src"] = "data:image/gif;base64,R0lGODlhAQABAAD/ACwAAAAAAQABAAACADs="
        if tag.name == "a":
            tag["href"] = "#"  # Retains link role without navigation.
    return "<!doctype html>\n" + str(soup)


def run_static_axe(safe_html: str, *, root: Path) -> dict[str, Any]:
    js_path = root / "node_modules" / "axe-core" / "axe.min.js"
    if not js_path.is_file():
        return unavailable("axe", "Install local axe-core using npm install.")
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            try:
                context = browser.new_context(service_workers="block", accept_downloads=False)
                try:
                    context.route("**/*", lambda route: route.abort())
                    page = context.new_page()
                    page.set_default_timeout(15000)
                    page.set_content(safe_html, wait_until="domcontentloaded", timeout=15000)
                    page.add_script_tag(path=str(js_path))
                    raw = page.evaluate(
                        "async rules => window.axe.run(document, "
                        "{runOnly: {type: 'rule', values: rules}})",
                        list(STATIC_AXE_RULES),
                    )
                finally:
                    context.close()
            finally:
                browser.close()
        result = normalize_axe(raw)
        result["limitations"].append(
            "Static semantic HTML only: no JavaScript application state, CSS contrast, "
            "user interactions or full accessibility conformance were tested."
        )
        result["metrics"]["static_rules"] = list(STATIC_AXE_RULES)
        return result
    except Exception as exc:  # noqa: BLE001 - optional diagnostics cannot abort the audit.
        return unavailable("axe", f"Static axe scan unavailable ({type(exc).__name__}).")


def run_static_impeccable(safe_html: str, *, root: Path) -> dict[str, Any]:
    binary = local_binary(root, "impeccable")
    if binary is None:
        return unavailable("impeccable", "Install local Impeccable using npm install.")
    # Fixed CLI and a generated HTML-only input; user URLs never appear as CLI args.
    with TemporaryDirectory(prefix="pagecheck-static-") as folder:
        file = Path(folder) / "snapshot.html"
        file.write_text(safe_html, encoding="utf-8")
        result = run_local_json_command(
            "impeccable", [str(binary), "detect", "--json", str(file)],
            root=root, timeout=40,
        )
    if result.get("status") == "completed":
        result["limitations"].append(
            "Design heuristics on sanitized HTML only; original styles and "
            "runtime layout were not assessed."
        )
    return result


def collect_static_engines(
    html: str, final_url: str, *, root: Path = ROOT,
    axe_runner: Callable[..., dict] = run_static_axe,
    impeccable_runner: Callable[..., dict] = run_static_impeccable,
) -> dict[str, Any]:
    """Collect safe-ish local static diagnostics, never navigate tools to URL."""
    validate_public_url(final_url)
    safe = sanitize_static_html(html)
    reports = {
        "lighthouse": unavailable(
            "lighthouse",
            "Not run on public URLs: Lighthouse launches its own network-enabled Chrome. "
            "Use the trusted localhost fixture test until network isolation exists.",
        ),
    }
    for engine, runner in (("axe", axe_runner), ("impeccable", impeccable_runner)):
        try:
            report = runner(safe, root=Path(root))
            reports[engine] = report if isinstance(report, dict) else unavailable(
                engine, "Engine returned an unexpected response."
            )
        except Exception as exc:  # noqa: BLE001 - isolate each optional engine.
            reports[engine] = unavailable(engine, f"Engine unavailable ({type(exc).__name__}).")
    return combine_engines(reports)
