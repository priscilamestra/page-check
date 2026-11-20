"""Readable, conservative audit-coverage explanations, independent of Streamlit.

Never upgrades a source to completed, infers a missing result was a defect, or
uses the aggregate number of not-verified checks as a count of page problems.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

SOURCE_DEFINITIONS = (
    ("seo", "Technical SEO", "SEO checks use extracted HTML, not Google rankings."),
    ("conversion", "Conversion HTML", "Links, forms and tracking are inspected without submitting anything."),
    ("desktop", "Desktop screenshot", "Guarded JavaScript rendering; no clicks or submissions."),
    ("mobile", "Mobile screenshot", "Guarded JavaScript rendering; no clicks or submissions."),
    ("axe", "Accessibility (axe-core)", "Static HTML semantics only; not full WCAG testing."),
    ("impeccable", "Design (Impeccable)", "Sanitized HTML heuristics; runtime layout still needs visual review."),
)

STATUS_LABELS = {
    "completed": "Completed",
    "partial": "Limited",
    "not_verified": "Not verified",
}


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    # Keep a single short explanatory line from diagnostic metadata, not a traceback.
    return " ".join(value.split())[:400]


def source_rows(report: Mapping[str, Any]) -> list[dict[str, str]]:
    """Status plus reason for each source, including older saved reports."""
    states = _mapping(report.get("source_states"))
    engines = _mapping(states.get("engines"))
    visuals = _mapping(states.get("visuals"))
    visual_capture = _mapping(report.get("visual_capture"))
    visual_errors = _mapping(visual_capture.get("errors"))
    visual_notes = _mapping(report.get("visual_limitations"))
    engine_notes = _mapping(report.get("engine_limitations"))
    rows: list[dict[str, str]] = []
    for key, title, description in SOURCE_DEFINITIONS:
        if key in {"seo", "conversion"}:
            raw = states.get(key)
        elif key in {"desktop", "mobile"}:
            raw = visuals.get(key)
        else:
            raw = engines.get(key)
        status = raw if raw in STATUS_LABELS else "not_verified"
        reason = ""
        if key in {"desktop", "mobile"}:
            reason = _text(visual_errors.get(key))
            if not reason:
                notes = visual_notes.get(key)
                if isinstance(notes, list):
                    reason = _text(next((v for v in notes if isinstance(v, str) and v.strip()), ""))
            if not reason and status == "not_verified":
                reason = ("Browser capture was not requested for this audit."
                          if not visual_capture else "No browser result or reason was recorded.")
        elif key in {"axe", "impeccable"}:
            notes = engine_notes.get(key)
            if isinstance(notes, list):
                valid_notes = [v for v in notes if isinstance(v, str) and v.strip()]
                if valid_notes:
                    # Successful static engines append their English scope note last;
                    # unavailable engines keep the first failure reason.
                    reason = _text(valid_notes[-1] if status == "completed" else valid_notes[0])
            if not reason and status == "not_verified":
                reason = "This tool did not produce a confirmed result."
        elif status == "not_verified":
            reason = "This source was not executed or its result is unavailable."
        rows.append({"id": key, "title": title, "status": status,
                     "status_label": STATUS_LABELS[status],
                     "description": description, "reason": reason})
    return rows


def not_verified_by_area(report: Mapping[str, Any]) -> list[tuple[str, int]]:
    """Explain large counts without conflating checks with defects."""
    modules = _mapping(_mapping(report.get("summary")).get("by_module"))
    counts: list[tuple[str, int]] = []
    for module, values in modules.items():
        if not isinstance(module, str):
            continue
        number = _mapping(values).get("not_verified", 0)
        if isinstance(number, int) and not isinstance(number, bool) and number > 0:
            counts.append((module, number))
    return sorted(counts, key=lambda pair: (-pair[1], pair[0]))


def screenshot_kind(report: Mapping[str, Any], viewport: str) -> str:
    """Name the actual evidence (full annotated versus first-viewport only)."""
    value = _mapping(_mapping(report.get("screenshots")).get(viewport))
    if value.get("annotated"):
        return "Annotated screenshot"
    if value.get("after_scroll"):
        return "Static screenshot"
    if value.get("initial"):
        return "Initial viewport only — limited evidence, no annotations"
    return "No screenshot"
