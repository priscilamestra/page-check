"""Small, honest part-to-whole visualization for seven audit sources."""
from __future__ import annotations

from html import escape
from collections.abc import Mapping


def source_composition_html(counts: Mapping[str, int]) -> str:
    labels = (("completed", "Completed", "#23856F"),
              ("partial", "Limited", "#C58A41"),
              ("not_verified", "Not verified", "#718096"))
    values = [max(0, n) if isinstance(n, int) and not isinstance(n, bool) else 0
              for key, _, _ in labels for n in [counts.get(key, 0)]]
    total = sum(values)
    if not total:
        return ""
    summary = ", ".join(f"{label}: {n} of {total}" for (_, label, _), n in zip(labels, values))
    html = [f'<div role="img" aria-label="{escape(summary, quote=True)}">',
            '<div style="height:29px;display:flex;overflow:hidden;border-radius:6px;'
            'width:100%;background:rgba(128,128,128,.16)">']
    for (_, label, color), value in zip(labels, values):
        if value:
            width = 100 * value / total
            html.append(f'<div style="width:{width:.5f}%;background:{color};'
                        'display:flex;align-items:center;justify-content:center;'
                        'color:white;font-weight:700;font-size:.85rem;'
                        f'border-right:1px solid rgba(0,0,0,.2)" title="{label}: {value} of {total}">'
                        f'{value}</div>')
    html.append('</div><div style="display:flex;flex-wrap:wrap;gap:8px 20px;margin:9px 0 16px">')
    for (_, label, color), value in zip(labels, values):
        html.append('<span style="font-size:.89rem">'
                    f'<span aria-hidden="true" style="color:{color}">●</span> '
                    f'<b>{label}</b>: {value} of {total}</span>')
    html.append('</div></div>')
    return "".join(html)
