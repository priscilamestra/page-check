"""Deterministic, offline exports: UTF-8 JSON/CSV and accessible HTML+PNG ZIP.

The exporter never executes audit engines and never loads arbitrary files from
screenshot paths: only existing local PNGs under the project's artifacts/ tree.
"""
from __future__ import annotations

import csv
import io
import json
import zipfile
from html import escape
from pathlib import Path
from typing import Any, Mapping

MAX_IMAGE_BYTES = 20 * 1024 * 1024


def json_export(report: Mapping[str, Any]) -> bytes:
    return json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False).encode("utf-8")


def _cell(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False)
    text = str(value)
    # Spreadsheet applications may interpret CSV content as formulas.
    if text.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")):
        return "'" + text
    return text


def findings_csv(report: Mapping[str, Any]) -> bytes:
    cols = ("priority", "status", "area", "issue", "recommended_fix", "team", "source", "viewport")
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer)
    writer.writerow(cols)
    for row in report.get("findings") or []:
        if not isinstance(row, Mapping):
            continue
        writer.writerow([_cell(row.get(key)) for key in (
            "severity", "status", "module", "title", "recommendation",
            "team", "source", "viewport",
        )])
    return ("\ufeff" + buffer.getvalue()).encode("utf-8")


def _screenshot(value: object, root: Path) -> Path | None:
    if not isinstance(value, (str, Path)) or not str(value).strip():
        return None
    allowed = (root / "artifacts").resolve()
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = root / candidate
    candidate = candidate.resolve()
    if not candidate.is_relative_to(allowed) or candidate.suffix.lower() != ".png":
        return None
    try:
        if not candidate.is_file() or not 0 < candidate.stat().st_size <= MAX_IMAGE_BYTES:
            return None
    except OSError:
        return None
    return candidate


def _visual_files(report: Mapping[str, Any], root: Path) -> dict[str, Path]:
    result: dict[str, Path] = {}
    shots = report.get("screenshots")
    if not isinstance(shots, Mapping):
        return result
    for viewport in ("desktop", "mobile"):
        records = shots.get(viewport)
        if not isinstance(records, Mapping):
            continue
        target = _screenshot(records.get("annotated") or records.get("after_scroll") or records.get("initial"), root)
        if target is not None:
            result[viewport] = target
    return result


def html_export(report: Mapping[str, Any], images: Mapping[str, Path] | None = None) -> bytes:
    """Self-contained HTML (except local PNG references packaged by zip_export)."""
    images = images or {}
    requested = escape(str(report.get("requested_url") or "Unknown URL"))
    final_url = escape(str(report.get("final_url") or ""))
    created = escape(str(report.get("saved_at") or report.get("collected_at") or "Not recorded"))
    niche = escape(str(report.get("niche") or ""))
    goal = escape(str(report.get("objective") or ""))
    status = escape(str(report.get("status") or "partial"))
    counts = (report.get("summary") or {}).get("counts") or {}
    scores = (report.get("scores") or {}).get("internal") or {}
    seo = scores.get("seo") or {}
    score = seo.get("score") if isinstance(seo, Mapping) else None
    score_text = f"{score:.0f}/100" if isinstance(score, (int, float)) and not isinstance(score, bool) else "Not verified"
    def number(key: str) -> str:
        return escape(str(counts.get(key, 0))) if isinstance(counts, Mapping) else "0"
    cards = "".join(
        f'<div class="metric"><span>{label}</span><strong>{value}</strong></div>'
        for label, value in (("Technical SEO (scored rules)", score_text), ("Issues", number("failed")),
                             ("Needs review", number("warning")),
                             ("Not verified", number("not_verified")))
    )
    blocks = []
    findings = report.get("findings") or []
    for row in findings:
        if not isinstance(row, Mapping):
            continue
        severity = escape(str(row.get("severity") or "info"))
        title = escape(str(row.get("title") or "Untitled finding"))
        details = escape(str(row.get("recommendation") or "Review the available evidence."))
        module = escape(str(row.get("module") or "Technical"))
        team = escape(str(row.get("team") or "Unassigned"))
        evidence = escape(json.dumps(row.get("evidence") or {}, ensure_ascii=False, indent=2, default=str))
        blocks.append(
            '<article class="finding"><div class="heading">'
            f'<span class="priority">{severity.upper()}</span><strong>{title}</strong></div>'
            f'<p>{details}</p><small>{module} · {team}</small>'
            f'<details><summary>Technical evidence</summary><pre>{evidence}</pre></details></article>'
        )
    visual_sections = []
    for viewport in ("desktop", "mobile"):
        if viewport in images:
            visual_sections.append(f'<figure><img src="screenshots/{viewport}.png" '
                                   f'alt="{viewport.capitalize()} audit screenshot" loading="lazy">'
                                   f'<figcaption>{viewport.capitalize()} visual evidence</figcaption></figure>')
    if not visual_sections:
        visual_sections.append('<p class="muted">No verified screenshots are available for this report.</p>')
    coverage = report.get("source_states") or {}
    coverage_html = "".join(
        f'<li><strong>{escape(str(k))}</strong>: '
        f'{escape(json.dumps(v, ensure_ascii=False))}</li>'
        for k, v in coverage.items()
    ) if isinstance(coverage, Mapping) else ""
    html = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Page Check audit — {requested}</title>
<style>
:root{{color-scheme:light;font-family:system-ui,Arial,sans-serif;color:#192b30;background:#f6f8f8}}
body{{margin:0 auto;max-width:1050px;padding:2rem 1rem;line-height:1.55}}
header{{border-bottom:3px solid #11665b;padding-bottom:1rem;margin-bottom:1.5rem}}
h1,h2{{line-height:1.2}}h1{{font-size:2rem}}.muted,small{{color:#50646a}}
.metrics{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:.8rem}}
.metric{{background:white;border:1px solid #d9e1e0;border-radius:10px;padding:1rem}}
.metric span{{display:block;color:#50646a}}.metric strong{{display:block;font-size:1.8rem}}
.finding{{background:white;border:1px solid #d9e1e0;border-radius:10px;padding:1rem;margin:.8rem 0;break-inside:avoid}}
.heading{{display:flex;gap:.65rem;align-items:center;flex-wrap:wrap}}.priority{{font-size:.8rem;background:#eaeef0;padding:.2rem .6rem;border-radius:20px}}
pre{{white-space:pre-wrap;overflow-wrap:anywhere;background:#f2f4f4;padding:.8rem}}
figure{{margin:1.5rem 0;background:white;padding:.7rem;border:1px solid #d9e1e0}}
figure img{{width:100%;height:auto;display:block}}figcaption{{color:#50646a;margin-top:.5rem}}
section{{margin-top:2rem}}details{{margin-top:.7rem}}a{{overflow-wrap:anywhere}}
@media print{{body{{max-width:none}}.finding,figure{{page-break-inside:avoid}}}}
</style></head><body>
<header><h1>Page Check · Audit report</h1><p>{requested}</p>
<p class="muted">Final URL: {final_url} · Niche: {niche} · Goal: {goal} · Saved: {created}</p>
<p><strong>Coverage:</strong> {status}. Unrun checks remain not verified; scores do not predict rankings or conversions.</p></header>
<section aria-label="Summary"><h2>Summary</h2><div class="metrics">{cards}</div></section>
<section aria-label="Findings"><h2>Findings ({len(blocks)})</h2>{''.join(blocks) if blocks else '<p>No findings in executed checks. This does not prove the page is error-free.</p>'}</section>
<section aria-label="Visual evidence"><h2>Visual evidence</h2>{''.join(visual_sections)}</section>
<section aria-label="Audit coverage"><h2>Checks performed</h2><ul>{coverage_html}</ul></section>
<footer><p class="muted">Generated by Page Check · Deterministic analysis · Source report.json is included in the archive.</p></footer>
</body></html>'''
    return html.encode("utf-8")


def zip_export(report: Mapping[str, Any], project_root: Path) -> bytes:
    """ZIP with HTML report, JSON, CSV findings, and existing audited PNGs."""
    root = Path(project_root).resolve()
    visuals = _visual_files(report, root)
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("report.html", html_export(report, visuals))
        archive.writestr("report.json", json_export(report))
        archive.writestr("findings.csv", findings_csv(report))
        archive.writestr("README.txt", "Open report.html in a browser. Evidence images are included only when locally available.\n")
        for viewport, path in visuals.items():
            archive.write(path, f"screenshots/{viewport}.png")
    return output.getvalue()
