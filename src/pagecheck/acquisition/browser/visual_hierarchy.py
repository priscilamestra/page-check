"""Bounded page-wide DOM design checks for a previously opened guarded browser.

These checks inspect the static rendered DOM throughout the document, not just
headings intersecting the screenshot. They are objective measurements, never a
subjective design score or evidence about JS-only content that was not loaded.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

# One bounded browser evaluation: no network, clicks, form values or script injection.
_DESIGN_SCRIPT = r"""() => {
  const MAX_HEADINGS = 160, MAX_TARGETS = 100, MAX_TEXT = 180;
  const vp = {width: window.innerWidth, height: window.innerHeight};
  function visible(el, rect, style) {
    return style.display !== 'none' && style.visibility !== 'hidden' &&
      Number(style.opacity || 1) > 0 && rect.width > 0 && rect.height > 0;
  }
  function selector(el) {
    // A short, non-sensitive DOM locator; never include input values.
    if (el.id && /^[a-zA-Z_][\w-]*$/.test(el.id))
      return '#' + el.id.slice(0, 80);
    const parts = [];
    for (let cur = el, depth = 0; cur && cur.tagName && depth < 4; cur = cur.parentElement, depth++) {
      const tag = cur.tagName.toLowerCase();
      let position = 1;
      for (let sibling = cur.previousElementSibling; sibling; sibling = sibling.previousElementSibling)
        if (sibling.tagName === cur.tagName) position++;
      parts.unshift(tag + ':nth-of-type(' + position + ')');
    }
    return parts.join(' > ').slice(0, 160);
  }
  function box(rect) {
    return {x: rect.left + window.scrollX, y: rect.top + window.scrollY,
            width: rect.width, height: rect.height};
  }
  const headings = [], targets = [], contrast = [];
  let totalHeadings = 0, totalTargets = 0, totalText = 0;
  for (const el of document.querySelectorAll('h1,h2,h3,h4,h5,h6')) {
    const rect = el.getBoundingClientRect(), st = getComputedStyle(el);
    if (!visible(el, rect, st)) continue;
    totalHeadings++;
    if (headings.length >= MAX_HEADINGS) continue;
    const px = Number.parseFloat(st.fontSize);
    if (Number.isFinite(px) && px > 0)
      headings.push({level: Number(el.tagName.slice(1)), font_px: px,
        text: (el.textContent || '').trim().slice(0, 80), selector: selector(el), box: box(rect)});
  }
  // Target sizes: only visible buttons, button roles, or links explicitly styled
  // as a button. Ordinary text links are not comparable to CTA touch targets.
  for (const el of document.querySelectorAll('button, input[type="submit"], [role="button"], a[class*="btn"], a[class*="button"], a[class*="cta"]')) {
    const rect = el.getBoundingClientRect(), st = getComputedStyle(el);
    if (!visible(el, rect, st)) continue;
    totalTargets++;
    if (targets.length >= MAX_TARGETS) continue;
    targets.push({tag: el.tagName.toLowerCase(),
      text: (el.getAttribute('aria-label') || el.getAttribute('value') ||
        el.textContent || '').trim().slice(0, 80), selector: selector(el), box: box(rect)});
  }
  function rgb(input) {
    const m = /^rgba?\(\s*(\d+(?:\.\d+)?)\s*[, ]\s*(\d+(?:\.\d+)?)\s*[, ]\s*(\d+(?:\.\d+)?)(?:\s*[,/]\s*([\d.]+))?\s*\)$/.exec(input || '');
    if (!m) return null;
    if (m[4] !== undefined && Number(m[4]) < .999) return null;
    return [Number(m[1]), Number(m[2]), Number(m[3])];
  }
  function luminance(c) {
    const rgbLinear = c.map(x => {const v = x / 255; return v <= .04045 ? v / 12.92 : Math.pow((v + .055) / 1.055, 2.4);});
    return .2126 * rgbLinear[0] + .7152 * rgbLinear[1] + .0722 * rgbLinear[2];
  }
  function background(el) {
    for (let current = el, depth = 0; current && depth < 12; current = current.parentElement, depth++) {
      const st = getComputedStyle(current);
      if (st.backgroundImage && st.backgroundImage !== 'none') return null;
      const c = rgb(st.backgroundColor);
      if (c) return c;
    }
    return null; // no provable opaque background, no contrast verdict
  }
  for (const el of document.querySelectorAll('h1,h2,h3,h4,h5,h6,p,li,button,a,[role="button"]')) {
    const rect = el.getBoundingClientRect(), st = getComputedStyle(el);
    if (!visible(el, rect, st) || !(el.textContent || '').trim()) continue;
    totalText++;
    if (contrast.length >= MAX_TEXT) continue;
    const fg = rgb(st.color), bg = background(el), px = Number.parseFloat(st.fontSize);
    if (!fg || !bg || !Number.isFinite(px)) continue;
    const a = luminance(fg), b = luminance(bg);
    const ratio = (Math.max(a,b) + .05) / (Math.min(a,b) + .05);
    const bold = Number.parseInt(st.fontWeight, 10) >= 700;
    const min = px >= 24 || (bold && px >= 18.66) ? 3 : 4.5;
    contrast.push({text: (el.textContent || '').trim().slice(0, 70),
      ratio: Math.round(ratio * 10) / 10, threshold: min,
      foreground: st.color, background: "rgb(" + bg.join(", ") + ")",
      selector: selector(el), box: box(rect)});
  }
  return {headings, targets, contrast, viewport_width: vp.width,
    viewport_height: vp.height, document_height: Math.max(document.body?.scrollHeight || 0,
    document.documentElement.scrollHeight), totals: {headings: totalHeadings,
    targets: totalTargets, text: totalText}, capped: {
      headings: totalHeadings > MAX_HEADINGS,
      targets: totalTargets > MAX_TARGETS,
      contrast: totalText > MAX_TEXT}};
}"""


def _box(obj: Mapping[str, Any]) -> dict | None:
    box = obj.get("box")
    return dict(box) if isinstance(box, Mapping) else None


def _category(status: str, details: str = "") -> dict[str, str]:
    return {"status": status, "detail": details}


def assess_heading_hierarchy(observation: object) -> dict[str, Any]:
    """Evaluate heading structure, solid-color text contrast and CTA sizes.

    Preserves legacy status semantics while returning separate, user-friendly
    category results. No overall aesthetic score is invented.
    """
    empty = {"status": "not_verified", "headings_checked": 0, "findings": [],
             "criteria": {"headings": _category("not_assessed"),
                          "contrast": _category("not_assessed"),
                          "cta": _category("not_assessed")},
             "scope": "rendered_dom"}
    if not isinstance(observation, Mapping) or not isinstance(observation.get("headings"), list):
        return empty
    items: list[dict[str, Any]] = []
    for obj in observation["headings"][:160]:
        if not isinstance(obj, Mapping):
            continue
        try:
            level = int(obj["level"])
            size = float(obj["font_px"])
        except (KeyError, TypeError, ValueError, OverflowError):
            continue
        if level not in range(1, 7) or not 0 < size < 400:
            continue
        items.append({"level": level, "font_px": size,
                      "text": str(obj.get("text") or "")[:80],
                      "selector": str(obj.get("selector") or "")[:160], "box": _box(obj)})
    findings: list[dict[str, Any]] = []
    first_by_level: dict[int, dict[str, Any]] = {}
    for heading in items:
        first_by_level.setdefault(heading["level"], heading)
    if 1 in first_by_level and 2 in first_by_level:
        h1, h2 = first_by_level[1], first_by_level[2]
        if h2["font_px"] > h1["font_px"] * 1.2:
            findings.append({
                "id": "design-heading-size", "category": "layout", "severity": "low",
                "status": "warning", "title": "Secondary heading appears larger than page title",
                "description": (f"H2 '{h2['text']}' is {h2['font_px']:g}px; "
                                f"H1 '{h1['text']}' is {h1['font_px']:g}px."),
                "action": "Review the H1/H2 typography to make the main heading easy to identify.",
                "owner": "Design / Frontend", "evidence": {"h1_font_px": h1["font_px"],
                    "h2_font_px": h2["font_px"], "h2_text": h2["text"], "selector": h2.get("selector", "")},
                "box": h2.get("box"),
            })
    for earlier, later in zip(items, items[1:]):
        if later["level"] > earlier["level"] + 1:
            findings.append({
                "id": "design-heading-level-jump", "category": "layout", "severity": "low",
                "status": "warning", "title": "Heading hierarchy skips a level",
                "description": f"H{earlier['level']} is followed by H{later['level']} ('{later['text']}').",
                "action": "Review the heading outline and use consecutive levels where appropriate.",
                "owner": "Content / Design", "evidence": {"from": f"h{earlier['level']}",
                    "to": f"h{later['level']}", "heading": later["text"],
                    "selector": later.get("selector", "")},
                "box": later.get("box"),
            })
            break
    headline_issue_count = len(findings)
    if headline_issue_count:
        heading_status = "needs_review"
    elif len(first_by_level) < 2:
        heading_status = "limited" if items else "not_assessed"
    else:
        heading_status = "no_issues"

    # CTA touch-target checks are scoped by device viewport; not a general CTA
    # effectiveness or conversion-rate assessment.
    controls = observation.get("targets")
    valid_controls = 0
    cta_issues = 0
    if isinstance(controls, list):
        for i, control in enumerate(controls[:100]):
            if not isinstance(control, Mapping) or not isinstance(control.get("box"), Mapping):
                continue
            try:
                width, height = float(control["box"]["width"]), float(control["box"]["height"])
            except (ValueError, TypeError, KeyError):
                continue
            if not (width > 0 and height > 0):
                continue
            valid_controls += 1
            if width >= 24 and height >= 24:
                continue
            cta_issues += 1
            findings.append({
                "id": f"design-small-target-{i}", "category": "layout", "severity": "low",
                "status": "warning", "title": "Interactive control may be too small",
                "description": (f"Control '{str(control.get('text') or control.get('tag') or 'button')[:50]}' "
                                f"measures {width:.0f}×{height:.0f}px."),
                "action": "Increase the clickable area to at least 24×24px or provide adequate spacing.",
                "owner": "Design / Frontend", "evidence": {"width_px": width,
                    "height_px": height, "label": str(control.get("text") or "")[:80],
                    "selector": str(control.get("selector") or "")[:160]},
                "box": _box(control),
            })
    cta_status = ("needs_review" if cta_issues else
                  "no_issues" if valid_controls else "not_assessed")

    samples = observation.get("contrast")
    contrast_checked = contrast_issues = 0
    if isinstance(samples, list):
        for i, sample in enumerate(samples[:180]):
            if not isinstance(sample, Mapping):
                continue
            try:
                ratio, threshold = float(sample["ratio"]), float(sample["threshold"])
            except (KeyError, ValueError, TypeError):
                continue
            if not (0 < ratio <= 21 and threshold in (3, 4.5)):
                continue
            contrast_checked += 1
            if ratio >= threshold:
                continue
            contrast_issues += 1
            findings.append({
                "id": f"design-text-contrast-{i}", "category": "layout", "severity": "medium",
                "status": "warning", "title": "Text may have insufficient contrast",
                "description": (f"Text '{str(sample.get('text') or '')[:50]}' has measured "
                                f"contrast {ratio:g}:1; expected at least {threshold:g}:1."),
                "action": "Adjust the text or background color and check the final rendering.",
                "owner": "Design / Frontend", "evidence": {"contrast_ratio": ratio,
                    "minimum_ratio": threshold, "text": str(sample.get("text") or "")[:70],
                    "selector": str(sample.get("selector") or "")[:160],
                    "foreground": str(sample.get("foreground") or "")[:50],
                    "background": str(sample.get("background") or "")[:50]},
                "box": _box(sample),
            })
    contrast_status = ("needs_review" if contrast_issues else
                       "no_issues" if contrast_checked else "not_assessed")

    totals = observation.get("totals")
    if not isinstance(totals, Mapping):
        totals = {}
    capped = observation.get("capped")
    if not isinstance(capped, Mapping):
        capped = {}
    any_limited = any(capped.get(k) is True for k in ("headings", "targets", "contrast"))
    status = ("needs_review" if findings else
              "limited" if heading_status == "limited" and not (contrast_checked or valid_controls) else
              "not_verified" if not (items or contrast_checked or valid_controls) else
              "limited" if any_limited else "no_measured_findings")
    return {
        "status": status, "headings_checked": len(items), "findings": findings,
        "scope": "rendered_dom", "truncated": any_limited,
        "criteria": {
            "headings": _category(heading_status, str(headline_issue_count) if headline_issue_count else ""),
            "contrast": _category(contrast_status, str(contrast_issues) if contrast_issues else ""),
            "cta": _category(cta_status, str(cta_issues) if cta_issues else ""),
        },
        "measurements": {"headings": len(items), "controls": valid_controls,
                         "contrast_samples": contrast_checked, "contrast_details_shown": contrast_issues,
                         "contrast_findings": contrast_issues, "cta_findings": cta_issues,
                         "document_height": totals.get("document_height", observation.get("document_height"))},
    }


def inspect_heading_hierarchy(page: Any) -> dict[str, Any]:
    """Inspect all rendered document headings and bounded visual DOM samples."""
    return assess_heading_hierarchy(page.evaluate(_DESIGN_SCRIPT))


def make_design_review(
    hierarchy: Mapping[str, Any], *, layout_findings: list[dict[str, Any]] | None = None,
    geometry_checked: bool = False, geometry_truncated: bool = False,
    screenshot_scope: str = "initial_viewport",
) -> dict[str, Any]:
    """Combine independently measured page-wide design categories for the UI."""
    findings = layout_findings or []
    categories = dict(hierarchy.get("criteria") or {})
    categories["layout"] = _category(
        "needs_review" if findings else
        "limited" if geometry_checked and geometry_truncated else
        "no_issues" if geometry_checked else "not_assessed",
        str(len(findings)) if findings else "",
    )
    return {
        "status": "needs_review" if findings or hierarchy.get("status") == "needs_review"
                  else hierarchy.get("status", "not_verified"),
        "scope": "rendered_document_dom", "screenshot_scope": screenshot_scope,
        "headings_checked": hierarchy.get("headings_checked", 0),
        "layout_findings": len(findings),
        "criteria": categories,
        "measurements": dict(hierarchy.get("measurements") or {}),
        "truncated": hierarchy.get("truncated") is True or geometry_truncated,
    }
