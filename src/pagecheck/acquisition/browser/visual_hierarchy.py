"""Bounded, deterministic heading-hierarchy observations for an already opened page.

The assessment is NOT an aesthetic score, nor a full-page design review.
The caller controls browser/network policies and the inspected viewport.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

_HEADING_SCRIPT = r"""() => {
  const vp = {width: window.innerWidth, height: window.innerHeight};
  const headers = [];
  for (const el of document.querySelectorAll('h1,h2,h3,h4,h5,h6')) {
    const rect = el.getBoundingClientRect();
    const style = getComputedStyle(el);
    if (style.display === 'none' || style.visibility === 'hidden' ||
        rect.width <= 0 || rect.height <= 0 || rect.bottom <= 0 ||
        rect.top >= vp.height || rect.right <= 0 || rect.left >= vp.width) continue;
    if (headers.length >= 24) break;
    const font = Number.parseFloat(style.fontSize);
    if (!Number.isFinite(font) || font <= 0) continue;
    headers.push({level: Number(el.tagName.substring(1)), font_px: font,
      text: (el.textContent || '').trim().slice(0, 80),
      box: {x: Math.max(0, rect.left), y: Math.max(0, rect.top),
            width: Math.min(rect.right, vp.width) - Math.max(0, rect.left),
            height: Math.min(rect.bottom, vp.height) - Math.max(0, rect.top)}});
  }
  return {headings: headers, viewport_width: vp.width, viewport_height: vp.height};
}"""


def assess_heading_hierarchy(observation: object) -> dict[str, Any]:
    """Flag only measured typographic inconsistencies in the visible viewport.

    Absence of headings is 'not_verified', never a positive evaluation.
    Results are advisory; large display headings can be intentional.
    """
    if not isinstance(observation, Mapping) or not isinstance(observation.get("headings"), list):
        return {"status": "not_verified", "headings_checked": 0, "findings": []}
    items = []
    for obj in observation["headings"][:24]:
        if not isinstance(obj, Mapping):
            continue
        try:
            level = int(obj["level"])
            size = float(obj["font_px"])
        except (KeyError, TypeError, ValueError, OverflowError):
            continue
        if level not in range(1, 7) or not 0 < size < 400:
            continue
        items.append({"level": level, "font_px": size, "text": str(obj.get("text") or "")[:80],
                      "box": obj.get("box")})
    if not items:
        return {"status": "not_verified", "headings_checked": 0, "findings": []}
    findings = []
    first_by_level = {}
    for heading in items:
        first_by_level.setdefault(heading["level"], heading)
    if 1 in first_by_level and 2 in first_by_level:
        h1, h2 = first_by_level[1], first_by_level[2]
        if h2["font_px"] > h1["font_px"] * 1.2:
            findings.append({
                "id": "design-heading-size", "category": "layout", "severity": "low",
                "status": "warning", "title": "Heading size may obscure page hierarchy",
                "description": f"Visible H2 is {h2['font_px']:g}px; visible H1 is {h1['font_px']:g}px.",
                "action": "Check whether the primary page heading is visually identifiable and intentional.",
                "owner": "Design / Frontend", "evidence": {"h1_font_px": h1["font_px"],
                    "h2_font_px": h2["font_px"], "h2_text": h2["text"]},
                "box": h2.get("box"),
            })
    # Only compare headings observed in reading order and inside the viewport.
    for earlier, later in zip(items, items[1:]):
        if later["level"] > earlier["level"] + 1:
            findings.append({
                "id": "design-heading-level-jump", "category": "layout", "severity": "low",
                "status": "warning", "title": "Heading hierarchy skips a level",
                "description": f"Visible H{earlier['level']} is followed by H{later['level']}.",
                "action": "Review heading levels for an understandable document outline.",
                "owner": "Content / Design", "evidence": {"from": f"h{earlier['level']}",
                    "to": f"h{later['level']}", "heading": later["text"]},
                "box": later.get("box"),
            })
            break
    if findings:
        status = "needs_review"
    elif len(first_by_level) < 2:
        status = "limited"
    else:
        status = "no_measured_findings"
    return {"status": status, "headings_checked": len(items), "findings": findings}


def inspect_heading_hierarchy(page: Any) -> dict[str, Any]:
    return assess_heading_hierarchy(page.evaluate(_HEADING_SCRIPT))
