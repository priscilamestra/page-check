"""Scrapling parser adapter; all network access stays in Page Check."""
from __future__ import annotations

from typing import Any
from urllib.parse import urljoin

from scrapling import Selector


def discover_links(html: str, page_url: str) -> list[dict[str, Any]]:
    """Discover anchors from already-fetched HTML without using Scrapling fetchers."""
    page = Selector(html, url=page_url, adaptive=False, huge_tree=False)
    links: list[dict[str, Any]] = []
    for index, element in enumerate(page.css("a[href]"), 1):
        href = str(element.attrib.get("href") or "").strip()
        if not href:
            continue
        links.append({
            "index": index,
            "text": " ".join(str(element.get_all_text(" ", strip=True)).split()),
            "href": href,
            "resolved_url": urljoin(page_url, href),
            "selector": str(element.generate_css_selector or ""),
            "element_html": str(element.html_content)[:1000],
            "discovered_by": "scrapling.Selector",
        })
    return links
