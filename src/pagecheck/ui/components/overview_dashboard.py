"""Small, accessible HTML visuals for the Streamlit audit Overview.

Presentation only. Values always come from the existing report summaries;
source completion and SEO scoring are deliberately not conflated.
All report-controlled strings are HTML-escaped before rendering.
"""
from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from html import escape
from typing import Any


OVERVIEW_STYLES = """
<style>
.pc-kpis{display:grid;grid-template-columns:minmax(0,.9fr) minmax(0,.9fr) minmax(0,.9fr) minmax(0,1.35fr);gap:10px;margin:8px 0 24px}
.pc-kpi,.pc-panel{border:1px solid rgba(135,145,160,.25);border-radius:12px;
 background:var(--secondary-background-color,rgba(120,120,120,.08));color:var(--text-color,inherit)}
.pc-kpi{padding:16px 14px;min-height:145px;display:flex;flex-direction:column;justify-content:space-between}
.pc-kpi-label{font-size:.83rem;font-weight:650;letter-spacing:.01em;opacity:.86;margin-bottom:8px}
.pc-kpi-main{font-size:2rem;line-height:1.1;font-weight:740;letter-spacing:-.04em;font-variant-numeric:tabular-nums}
/* Keep the SEO card focused on its approved metric: label + centered ring. */
.pc-kpi-seo{justify-content:flex-start}
.pc-kpi-seo .pc-kpi-inline{flex:1;align-items:center;justify-content:center;gap:0}
.pc-kpi-seo .pc-donut{width:92px;height:92px}
.pc-kpi-seo .pc-donut-hole{width:70px;height:70px;font-size:1.27rem}
.pc-kpi-inline{display:flex;flex-direction:column;align-items:flex-start;gap:4px}
.pc-donut{--pct:0%;--accent:#269d80;flex:0 0 auto;width:69px;height:69px;border-radius:50%;
 background:conic-gradient(var(--accent) 0% var(--pct),rgba(127,127,127,.24) var(--pct) 100%);
 display:grid;place-items:center}
.pc-donut-hole{width:53px;height:53px;display:grid;place-items:center;border-radius:50%;
 background:var(--secondary-background-color,#202124);font-size:1.06rem;font-weight:750;
 letter-spacing:-.05em;font-variant-numeric:tabular-nums;color:var(--text-color,#f5f5f5)}
.pc-kpi-value-green{color:#35b99a}.pc-kpi-value-red{color:#e77580}.pc-kpi-value-amber{color:#e7ac55}
.pc-progress{display:flex;height:7px;overflow:hidden;background:rgba(128,128,128,.2);border-radius:9px;margin-top:13px}
.pc-progress > span{height:100%}.pc-progress-ok{background:#269d80}.pc-progress-partial{background:#d49a45}.pc-progress-missing{background:#8492a8}
.pc-findings{border:1px solid rgba(135,145,160,.25);border-radius:12px;overflow:hidden;margin:10px 0 18px}
.pc-finding{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:14px;align-items:center;
 padding:14px 17px;background:var(--secondary-background-color,rgba(120,120,120,.08))}
.pc-finding + .pc-finding{border-top:1px solid rgba(135,145,160,.22)}
.pc-finding-title{font-size:.92rem;font-weight:650;line-height:1.3;margin-bottom:4px}
.pc-finding-summary{font-size:.79rem;opacity:.74;line-height:1.45}
.pc-finding-meta{font-size:.72rem;opacity:.66;margin-top:5px}
.pc-pill{display:inline-block;white-space:nowrap;border-radius:6px;padding:5px 9px;
 font-size:.72rem;font-weight:650;border:1px solid rgba(135,145,160,.24)}
.pc-pill-issue{color:#f5a0a7;background:rgba(223,78,96,.13)}
.pc-pill-review{color:#eac080;background:rgba(225,163,71,.14)}
.pc-pill-review-low{color:#b9c0ca;background:rgba(130,140,152,.14)}
.pc-coverage-key{display:flex;flex-wrap:wrap;gap:5px 11px;margin-top:9px;font-size:.72rem;line-height:1.3}
.pc-coverage-key span{white-space:nowrap}.pc-key-dot{display:inline-block;width:7px;height:7px;border-radius:50%;margin-right:4px;vertical-align:middle}
.pc-area-chart{border:1px solid rgba(135,145,160,.25);border-radius:12px;
 padding:15px 17px 6px;background:var(--secondary-background-color,rgba(120,120,120,.08));margin:6px 0 8px}
.pc-area-row{display:grid;grid-template-columns:minmax(95px,1fr) minmax(90px,2fr) auto;
 gap:12px;align-items:center;margin:0 0 16px}
.pc-area-label{font-weight:620;font-size:.82rem;overflow-wrap:anywhere}
.pc-area-value{font-size:.78rem;font-variant-numeric:tabular-nums;opacity:.85;min-width:32px;text-align:right}
.pc-area-bar{height:12px;background:rgba(128,128,128,.19);border-radius:6px;overflow:hidden;display:flex}
.pc-area-issues{background:#de6b78;height:100%}.pc-area-review{background:#d6a04e;height:100%}
.pc-chart-legend{display:flex;gap:18px;flex-wrap:wrap;font-size:.75rem;opacity:.79;margin:8px 0 13px}
.pc-dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px}
@media(max-width:900px){.pc-kpis{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:610px){.pc-kpis{grid-template-columns:1fr}.pc-finding{grid-template-columns:1fr;gap:8px}
 .pc-area-row{grid-template-columns:minmax(85px,1fr) minmax(90px,2fr) auto;gap:8px}}
</style>
"""


def _nonnegative(value: object) -> int:
    return value if type(value) is int and value >= 0 else 0


def _score_value(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if not math.isfinite(value) or not 0 <= value <= 100:
        return None
    return round(value)


def _area_label(value: object) -> str:
    raw = str(value or "Other").replace("_", " ").strip()
    return " ".join(word.upper() if word.lower() in {"seo", "url", "ux", "ui", "html", "api"}
                    else word.capitalize() for word in raw.split()) or "Other"


def _safe_text(value: object, limit: int = 160) -> str:
    text = " ".join(str(value or "").split())
    if len(text) > limit:
        text = text[: limit - 1].rstrip() + "…"
    return escape(text)


def metric_cards_html(
    *, seo_score: object, seo_partial: bool, issues: int, reviews: int,
    completed: int, partial: int, not_verified: int,
) -> str:
    """Four compact cards: measured SEO score, issues, reviews, source coverage."""
    score = _score_value(seo_score)
    completed, partial, not_verified = map(_nonnegative, (completed, partial, not_verified))
    total = completed + partial + not_verified
    if score is None:
        ring = '<div class="pc-donut" style="--pct:0%;--accent:#8492a8"><span class="pc-donut-hole">—</span></div>'
    else:
        ring = (f'<div class="pc-donut" role="img" aria-label="Technical SEO score: {score} out of 100" style="--pct:{score}%;--accent:#269d80">'
                f'<span class="pc-donut-hole">{score}</span></div>')
    done_width = completed / total * 100 if total else 0
    partial_width = partial / total * 100 if total else 0
    missing_width = not_verified / total * 100 if total else 0
    source_label = f"{completed}/{total}" if total else "—"
    return (
        '<section class="pc-kpis" aria-label="Audit summary">'
        '<div class="pc-kpi pc-kpi-seo"><div class="pc-kpi-label">Technical SEO</div>'
        f'<div class="pc-kpi-inline">{ring}</div></div>'
        '<div class="pc-kpi"><div class="pc-kpi-label">Confirmed issues</div>'
        f'<div class="pc-kpi-main pc-kpi-value-red">{_nonnegative(issues)}</div>'
        '</div>'
        '<div class="pc-kpi"><div class="pc-kpi-label">Needs review</div>'
        f'<div class="pc-kpi-main pc-kpi-value-amber">{_nonnegative(reviews)}</div>'
        '</div>'
        '<div class="pc-kpi"><div class="pc-kpi-label">Sources completed</div>'
        f'<div class="pc-kpi-main">{source_label}</div>'
        '<div class="pc-progress" role="img" aria-label="'
        f'{completed} completed, {partial} limited, {not_verified} not verified">'
        f'<span class="pc-progress-ok" style="width:{done_width:.3f}%"></span>'
        f'<span class="pc-progress-partial" style="width:{partial_width:.3f}%"></span>'
        f'<span class="pc-progress-missing" style="width:{missing_width:.3f}%"></span>'
        '</div>'
        '<div class="pc-coverage-key">'
        f'<span><i class="pc-key-dot" style="background:#269d80"></i>{completed} completed</span>'
        f'<span><i class="pc-key-dot" style="background:#d49a45"></i>{partial} limited</span>'
        f'<span><i class="pc-key-dot" style="background:#8492a8"></i>{not_verified} not verified</span>'
        '</div></div>'
        '</section>'
    )


def findings_html(rows: Sequence[Mapping[str, Any]]) -> str:
    """Present the highest-priority findings as short scannable rows, never as prose cards."""
    if not rows:
        return ""
    parts = ['<section class="pc-findings" aria-label="Priority findings">']
    for row in rows:
        status = row.get("status")
        issue = status == "failed"
        label = "Issue" if issue else "Needs review"
        severity_name = str(row.get("severity") or "info").lower()
        pill_style = ("issue" if issue else ("review-low" if severity_name in {"low", "info"} else "review"))
        severity = _safe_text(str(row.get("severity") or "info").title(), 35)
        area = _safe_text(_area_label(row.get("area")), 70)
        count = _nonnegative(row.get("occurrences"))
        if count > 1:
            area += f" · {count} occurrences"
        title = _safe_text(row.get("title") or "Untitled finding", 130)
        recommendation = _safe_text(row.get("recommendation"), 155)
        parts.append(
            '<div class="pc-finding"><div>'
            f'<div class="pc-finding-title">{title}</div>'
            + (f'<div class="pc-finding-summary">{recommendation}</div>' if recommendation else '')
            + f'<div class="pc-finding-meta">{area}</div></div>'
            f'<div><span class="pc-pill pc-pill-{pill_style}">'
            f'{severity} · {label}</span></div></div>'
        )
    parts.append('</section>')
    return "".join(parts)


def area_chart_html(rows: Sequence[Mapping[str, Any]], *, limit: int = 6) -> str:
    """Stack only confirmed issues and reviews by module; no fabricated area scores."""
    valid = [(row, _nonnegative(row.get("issues")), _nonnegative(row.get("reviews")))
             for row in rows if isinstance(row, Mapping)]
    valid = [(row, issues, reviews) for row, issues, reviews in valid if issues + reviews > 0][:limit]
    if not valid:
        return ""
    maximum = max(issues + reviews for _, issues, reviews in valid)
    parts = ['<div class="pc-area-chart" role="img" aria-label="Findings by area: confirmed issues and review items">']
    for row, issues, reviews in valid:
        issue_width = 100 * issues / maximum
        review_width = 100 * reviews / maximum
        label = _safe_text(_area_label(row.get("area")), 60)
        parts.append(
            '<div class="pc-area-row">'
            f'<div class="pc-area-label">{label}</div>'
            '<div class="pc-area-bar">'
            f'<span class="pc-area-issues" style="width:{issue_width:.3f}%"></span>'
            f'<span class="pc-area-review" style="width:{review_width:.3f}%"></span>'
            '</div>'
            f'<div class="pc-area-value">{issues + reviews}</div></div>'
        )
    parts.append(
        '<div class="pc-chart-legend">'
        '<span><i class="pc-dot" style="background:#de6b78"></i>Confirmed issues</span>'
        '<span><i class="pc-dot" style="background:#d6a04e"></i>Needs review</span>'
        '</div></div>'
    )
    return "".join(parts)
