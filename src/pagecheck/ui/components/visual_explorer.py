"""Stage 19C: trustworthy, bounded screenshot presentation metadata.

Only local files already accepted by Page Check's path restrictions may appear.
The presence of a screenshot must not upgrade partial coverage to completed.
"""
from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pagecheck.ui.components.coverage_details import screenshot_kind, source_rows
from pagecheck.ui.components.report_data import safe_screenshot_path


def visual_cards(report: Mapping[str, Any], root: Path) -> list[dict[str, Any]]:
    source_map = {row["id"]: row for row in source_rows(report)}
    raw = report.get("screenshots") or {}
    screenshots = raw if isinstance(raw, Mapping) else {}
    cards = []
    for viewport in ("desktop", "mobile"):
        source = source_map[viewport]
        entry = screenshots.get(viewport) or {}
        paths = entry if isinstance(entry, Mapping) else {}
        annotated = safe_screenshot_path(paths.get("annotated"), root)
        scrolled = safe_screenshot_path(paths.get("after_scroll"), root)
        initial = safe_screenshot_path(paths.get("initial"), root)
        selected = annotated or scrolled or initial
        is_annotated = selected is not None and annotated == selected
        cards.append({
            "viewport": viewport,
            "title": viewport.title(),
            "status": source["status"],
            "status_label": source["status_label"],
            "description": source["description"],
            "reason": source["reason"],
            "path": selected,
            "kind": screenshot_kind(report, viewport) if selected else "No screenshot available",
            "annotated": is_annotated,
            "is_partial": source["status"] == "partial" or (selected is not None and
                          selected == initial and annotated is None and scrolled is None),
        })
    return cards


def visual_observations(report: Mapping[str, Any], viewport: str) -> list[dict[str, str]]:
    """Only findings explicitly tied to the requested viewport; no invented markers."""
    raw = report.get("findings") or []
    if not isinstance(raw, list):
        return []
    output = []
    for finding in raw:
        if not isinstance(finding, Mapping):
            continue
        evidence = finding.get("evidence")
        evidence = evidence if isinstance(evidence, Mapping) else {}
        noted_viewport = finding.get("viewport") or evidence.get("viewport")
        if noted_viewport != viewport or finding.get("status") not in {"failed", "warning"}:
            continue
        output.append({
            "title": str(finding.get("title") or "Visual finding"),
            "status": str(finding.get("status")),
            "severity": str(finding.get("severity") or "info"),
        })
    return output
