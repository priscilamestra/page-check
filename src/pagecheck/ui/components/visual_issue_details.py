"""User-facing, evidence-based screenshot explanations with bounded HTML rendering.

No rule is inferred from the screenshot alone: all details come from stored
Playwright check evidence. Category colors mirror the annotated PNG.
"""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from html import escape
from typing import Any

from pagecheck.reporting.annotations.marker_style import (
    CATEGORY_COLORS, CATEGORY_LABELS, CATEGORY_ORDER, finding_category, marker_color,
)

ISSUE_DETAIL_STYLES = """
<style>
.pc-visual-chips{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;margin:9px 0 13px}
.pc-visual-chip{border-left:3px solid var(--pc-accent);background:color-mix(in srgb,var(--pc-accent) 12%,transparent);
 border-radius:7px;padding:7px 9px;font-size:.83rem;line-height:1.45;overflow-wrap:anywhere;min-width:0}
.pc-visual-chip strong{color:inherit;font-weight:750}
.pc-visual-chip{color:var(--text-color,#f4f4f4)}
@media (forced-colors:active){.pc-visual-chip{border:1px solid CanvasText}}
.pc-visual-section{margin:15px 0 8px;border-left:3px solid var(--pc-accent);padding:0 0 0 12px}
.pc-visual-section-title{color:var(--pc-accent);font-size:.91rem;font-weight:700;margin:0 0 8px}
.pc-visual-item{padding:9px 0;border-bottom:1px solid rgba(135,145,160,.22)}
.pc-visual-item:last-child{border-bottom:none}
.pc-visual-element{font-size:.88rem;font-weight:650;line-height:1.45;overflow-wrap:anywhere}
.pc-visual-measure{font-size:.80rem;line-height:1.5;margin-top:4px}
.pc-visual-fix{font-size:.80rem;line-height:1.5;margin-top:3px;opacity:.9}
.pc-visual-location{font-size:.73rem;opacity:.70;overflow-wrap:anywhere;margin-top:5px}
.pc-visual-marker{display:inline-block;background:var(--pc-accent);color:#171717;border-radius:5px;
 font-size:.70rem;font-weight:800;min-width:23px;padding:2px 5px;text-align:center;margin-right:5px}
@media(max-width:500px){.pc-visual-chips{grid-template-columns:1fr}}
</style>
"""


def _safe(value: object, max_length: int = 145) -> str:
    string = " ".join(str(value or "").split())
    return escape(string[:max_length] + ("…" if len(string) > max_length else ""), quote=True)


def _numeric(evidence: Mapping, key: str) -> float | None:
    value = evidence.get(key)
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    import math
    return number if math.isfinite(number) and number >= 0 else None


def _location(evidence: Mapping) -> str:
    selector = evidence.get("selector")
    if isinstance(selector, str) and selector.strip():
        return "Element: " + _safe(selector, 160)
    box = evidence.get("box")
    if isinstance(box, Mapping):
        x, y = _numeric(box, "x"), _numeric(box, "y")
        if x is not None and y is not None:
            return f"Position: x={x:.0f}, y={y:.0f}px"
    return ""


def _detail(item: Mapping[str, Any]) -> tuple[str, str, str]:
    """Return specific element, measurement and remedy, never a generic repeated title."""
    evidence = item.get("evidence") or {}
    if not isinstance(evidence, Mapping):
        evidence = {}
    category = finding_category(item)
    title = str(item.get("title") or "Check needs review")
    action = str(item.get("recommendation") or "")
    description = str(item.get("description") or "")
    if category == "contrast":
        label = evidence.get("text") or "Unnamed text element"
        ratio, minimum = _numeric(evidence, "contrast_ratio"), _numeric(evidence, "minimum_ratio")
        observed = (f"Measured contrast: {ratio:g}:1 · minimum {minimum:g}:1"
                    if ratio is not None and minimum is not None else description)
        fg, bg = evidence.get("foreground"), evidence.get("background")
        if fg and bg:
            observed += f" · text {str(fg)[:48]} on {str(bg)[:48]}"
        fix = (f"Adjust the text or background color to reach at least {minimum:g}:1."
               if minimum is not None else action)
        return 'Text: “' + str(label) + '”', observed, fix
    if category == "buttons":
        label = evidence.get("label") or "Unnamed interactive control"
        width, height = _numeric(evidence, "width_px"), _numeric(evidence, "height_px")
        observed = (f"Clickable area: {width:g} × {height:g}px · minimum 24 × 24px"
                    if width is not None and height is not None else description)
        return 'Control: “' + str(label) + '”', observed, (
            "Increase its clickable area to at least 24 × 24px or provide sufficient spacing."
        )
    if category == "images":
        src = evidence.get("src") or evidence.get("data_src") or ""
        alt = evidence.get("alt") or ""
        element = 'Image: “' + str(alt) + '”' if alt else "Image element"
        observed = ("Source: " + str(src)) if src else description
        if evidence.get("capture_only") is True:
            observed += " · Missing in the restricted capture; not a confirmed website error."
        return element, observed, action or "Check the image source and lazy loading in a normal browser."
    if category == "titles":
        label = evidence.get("heading") or evidence.get("h2_text") or ""
        return ('Heading: “' + str(label) + '”' if label else title,
                description, action)
    if category == "layout":
        return title, description, action
    return title, description, action


def design_chips_html(review: Mapping[str, Any]) -> str:
    """Four differently colored category chips; colors also govern screenshot marks."""
    criteria = review.get("criteria")
    criteria = criteria if isinstance(criteria, Mapping) else {}
    chunks = ['<div class="pc-visual-chips" aria-label="Design checks by category">']
    for category, field in (("titles", "headings"), ("contrast", "contrast"),
                            ("buttons", "cta"), ("layout", "layout")):
        entry = criteria.get(field)
        entry = entry if isinstance(entry, Mapping) else {}
        status = entry.get("status", "not_assessed")
        raw_number = entry.get("detail")
        try:
            number = int(raw_number) if raw_number not in (None, "") else 0
        except (ValueError, TypeError):
            number = 0
        if status == "needs_review":
            state = f"{number} to review" if number > 0 else "Needs review"
        elif status == "no_issues":
            state = "No issues measured"
        elif status == "limited":
            state = "Partially assessed"
        else:
            state = "Not assessed"
        accent = CATEGORY_COLORS[category]
        chunks.append(f'<div class="pc-visual-chip" style="--pc-accent:{accent}">'
                      f'<strong>{CATEGORY_LABELS[category]}:</strong> {state}</div>')
    chunks.append('</div>')
    return ''.join(chunks)



def grouped_observations(observations: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Group identical categories without discarding any location or marker ID.

    Each result includes its original finding records; grouping is UI-only.
    """
    groups: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for finding in observations:
        if isinstance(finding, Mapping):
            groups[finding_category(finding)].append(finding)
    return [
        {"category": category, "label": CATEGORY_LABELS[category],
         "count": len(groups[category]), "findings": groups[category]}
        for category in CATEGORY_ORDER if groups.get(category)
    ]

def marker_numbers(observations: Sequence[Mapping[str, Any]], *, annotated: bool = True) -> set[int]:
    """Actual distinct numbered marks linked by annotate_screenshot().

    Do not count every finding as a visible mark: multiple findings may share
    one bounding box, and findings outside the captured image receive no ID.
    """
    if not annotated:
        return set()
    numbers: set[int] = set()
    for finding in observations:
        if not isinstance(finding, Mapping):
            continue
        evidence = finding.get("evidence")
        if isinstance(evidence, Mapping):
            number = evidence.get("marker_number")
            if type(number) is int and number > 0:
                numbers.add(number)
    return numbers


def marker_summary(observations: Sequence[Mapping[str, Any]], *, annotated: bool = True) -> dict[str, int]:
    """Keep audit findings and screenshot markers as separate measurements."""
    return {"findings": len(observations),
            "markers": len(marker_numbers(observations, annotated=annotated))}


def screenshot_findings_label(observations: Sequence[Mapping[str, Any]], *,
                              annotated: bool = True, name: str = "What to fix") -> str:
    """Show only actionable finding counts; don't expose marker counts in UI."""
    count = len(observations)
    word = "finding" if count == 1 else "findings"
    return f"{name} · {count} {word}"


# Target only this tab's keyed Streamlit containers. No styling leaks to
# unrelated expanders, and all controls keep Streamlit's native focus/keyboard behavior.
ISSUE_ACCORDION_STYLES = """
<style>
""" + "\n".join(
    f""".st-key-pc_fix_desktop_{category}, .st-key-pc_fix_mobile_{category} {{
  --pc-finding-accent: {color};
}}
:is(.st-key-pc_fix_desktop_{category}, .st-key-pc_fix_mobile_{category})
 [data-testid="stExpander"] details {{
  border-color: color-mix(in srgb, var(--pc-finding-accent) 48%, transparent);
  background: color-mix(in srgb, var(--pc-finding-accent) 9%, transparent);
  border-radius: 8px;
}}
:is(.st-key-pc_fix_desktop_{category}, .st-key-pc_fix_mobile_{category})
 [data-testid="stExpander"] details > summary {{
  border-left: 4px solid var(--pc-finding-accent);
  border-radius: 7px;
  padding-left: 13px;
  font-weight: 600;
}}
:is(.st-key-pc_fix_desktop_{category}, .st-key-pc_fix_mobile_{category})
 [data-testid="stExpander"] details > summary:focus-visible {{
  outline: 2px solid var(--pc-finding-accent);
  outline-offset: 2px;
}}
""" for category, color in CATEGORY_COLORS.items()
) + """
@media (forced-colors: active) {
  [class*="st-key-pc_fix_"] [data-testid="stExpander"] details > summary {
    border-left: 4px solid CanvasText;
  }
}
</style>
"""


def detailed_observations_html(observations: Sequence[Mapping[str, Any]]) -> str:
    """Show evidence and fixes by element, mapped to actual screenshot marker numbers."""
    groups: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for finding in observations:
        if isinstance(finding, Mapping):
            groups[finding_category(finding)].append(finding)
    parts = [ISSUE_DETAIL_STYLES]
    for category in CATEGORY_ORDER:
        rows = groups.get(category) or []
        if not rows:
            continue
        # Colors distinguish categories, but a confirmed failure marker uses red.
        color = CATEGORY_COLORS[category]
        parts.append(f'<section class="pc-visual-section" style="--pc-accent:{color}">'
                     f'<div class="pc-visual-section-title">{CATEGORY_LABELS[category]} '
                     f'· {len(rows)} location{"s" if len(rows) != 1 else ""}</div>')
        for row in rows:
            element, measure, fix = _detail(row)
            evidence = row.get("evidence")
            evidence = evidence if isinstance(evidence, Mapping) else {}
            number = evidence.get("marker_number")
            has_marker = type(number) is int and number > 0
            actual_color = evidence.get("marker_color")
            if actual_color not in {*CATEGORY_COLORS.values(), "#E46A70"}:
                actual_color = marker_color(row)
            marker = (f'<span class="pc-visual-marker" style="--pc-accent:{actual_color}" ' 
                      f'aria-label="Screenshot marker {number}">#{number}</span>' if has_marker else "")
            location = _location(evidence)
            parts.append('<div class="pc-visual-item">'
                         f'<div class="pc-visual-element">{marker}{_safe(element, 130)}</div>')
            if measure:
                # HTML may contain escaped color data added by _detail; escape once at output.
                parts.append(f'<div class="pc-visual-measure">{_safe(measure, 260)}</div>')
            if fix:
                parts.append(f'<div class="pc-visual-fix"><strong>Fix:</strong> '
                             f'{_safe(fix, 220)}</div>')
            if location:
                parts.append(f'<div class="pc-visual-location">{location}</div>')
            parts.append('</div>')
        parts.append('</section>')
    return ''.join(parts)
