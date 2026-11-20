"""Selected deterministic site rules adapted from jev-seo (MIT).

Rule concepts: https://github.com/AgriciDaniel/jev-seo/blob/main/jevseo/checks.py
No Jev, TypeSafe, DataForSEO, model scoring or external service is used.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any


def _duplicate_check(rule_id: str, field: str, label: str,
                     pages: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[str]] = defaultdict(list)
    observed: dict[str, str] = {}
    for page in pages:
        value = str(page.get(field) or "").strip()
        url = str(page.get("url") or "")
        if value and url:
            key = " ".join(value.casefold().split())
            grouped[key].append(url)
            observed[key] = value
    duplicates = [
        {"observed_value": observed[key], "urls": urls}
        for key, urls in grouped.items() if len(urls) > 1
    ]
    return {
        "check_id": rule_id,
        "module": "seo",
        "status": "warning" if duplicates else "passed",
        "severity": "medium" if duplicates else "info",
        "title": f"Duplicate {label}s across crawled pages" if duplicates else
                 f"Crawled pages use unique {label}s",
        "team": "SEO / Content",
        "evidence": {
            "source": "limited_safe_crawl",
            "pages_checked": len(pages),
            "duplicate_groups": duplicates,
        },
        "recommendation": (
            f"Give each crawled page a distinct {label} that describes that page."
            if duplicates else ""
        ),
    }


def audit_crawled_pages(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Run two cross-page rules without changing the single-page SEO score."""
    html_pages = [page for page in pages if page.get("status_code") == 200]
    return [
        _duplicate_check("SEO_SITE_UNIQUE_TITLES", "title", "page title", html_pages),
        _duplicate_check(
            "SEO_SITE_UNIQUE_DESCRIPTIONS", "meta_description", "meta description", html_pages
        ),
    ]
