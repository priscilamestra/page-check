"""Small, sequential, robots-aware crawl over Page Check's safe GET transport."""
from __future__ import annotations

import os
import time
import urllib.robotparser
from collections import deque
from collections.abc import Callable
from typing import Any
from urllib.parse import urldefrag, urlsplit, urlunsplit

from bs4 import BeautifulSoup

from pagecheck.acquisition.http.fetcher import (
    FetchedPage,
    FetchedResource,
    FetchError,
    fetch_resource,
)
from pagecheck.acquisition.http.parser import parse_html
from pagecheck.acquisition.http.scrapling_adapter import discover_links

USER_AGENT = "PageCheck"
HTML_TYPES = {"text/html", "application/xhtml+xml"}
DEFAULT_MAX_PAGES = 20
DEFAULT_MAX_DEPTH = 2
DEFAULT_MAX_LINKS = 200
DEFAULT_TIME_BUDGET_SECONDS = 90.0


def _configured_int(name: str, default: int, minimum: int, maximum: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    value = int(raw)
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}.")
    return value


def _configured_float(name: str, default: float, minimum: float, maximum: float) -> float:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    value = float(raw)
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}.")
    return value


def _url_key(url: str) -> str:
    clean, _ = urldefrag(url)
    parsed = urlsplit(clean)
    path = parsed.path or "/"
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), path, parsed.query, ""))


def _fragment_exists(html: str, fragment: str) -> bool:
    soup = BeautifulSoup(html, "html.parser")
    return bool(soup.find(id=fragment) or soup.find("a", attrs={"name": fragment}))


def _page_record(url: str, status_code: int, html: str) -> dict[str, Any]:
    parsed = parse_html(html, url)
    return {
        "url": url,
        "status_code": status_code,
        "title": parsed.get("title"),
        "meta_description": parsed.get("meta_description"),
        "canonical": parsed.get("canonical"),
        "meta_robots": parsed.get("meta_robots"),
    }


def _check(index: int, record: dict[str, Any]) -> dict[str, Any]:
    state = record["state"]
    status = {"valid": "passed", "broken": "failed", "needs_review": "warning",
              "not_tested": "not_verified"}[state]
    title = {
        "valid": "Link destination verified",
        "broken": "Broken internal link confirmed",
        "needs_review": "Link destination needs review",
        "not_tested": "Link destination was not tested",
    }[state]
    recommendation = {
        "valid": "",
        "broken": "Update or remove the link, or restore the destination.",
        "needs_review": "Link directly to the final URL and confirm the destination is intentional.",
        "not_tested": "Review the recorded limitation before treating this destination as valid or broken.",
    }[state]
    return {
        "check_id": f"CRAWL_LINK_{index}",
        "module": "navigation",
        "status": status,
        "severity": "high" if state == "broken" else "low" if state == "needs_review" else "info",
        "title": title,
        "team": "Frontend / SEO",
        "evidence": record,
        "recommendation": recommendation,
    }


def crawl_public_site(start: FetchedPage, *,
                      fetch: Callable[[str], FetchedResource] = fetch_resource,
                      discover: Callable[[str, str], list[dict[str, Any]]] = discover_links,
                      max_pages: int | None = None, max_depth: int | None = None,
                      max_links: int | None = None,
                      time_budget_seconds: float | None = None) -> dict[str, Any]:
    """Discover internal pages with Scrapling; fetch only via the guarded GET client."""
    max_pages = int(max_pages if max_pages is not None else _configured_int(
        "PAGECHECK_CRAWL_MAX_PAGES", DEFAULT_MAX_PAGES, 1, 50))
    max_depth = int(max_depth if max_depth is not None else _configured_int(
        "PAGECHECK_CRAWL_MAX_DEPTH", DEFAULT_MAX_DEPTH, 0, 4))
    max_links = int(max_links if max_links is not None else _configured_int(
        "PAGECHECK_CRAWL_MAX_LINKS", DEFAULT_MAX_LINKS, 1, 500))
    time_budget_seconds = float(
        time_budget_seconds if time_budget_seconds is not None else _configured_float(
            "PAGECHECK_CRAWL_TIME_BUDGET_SECONDS", DEFAULT_TIME_BUDGET_SECONDS, 1.0, 600.0
        )
    )
    if not 1 <= max_pages <= 50 or not 0 <= max_depth <= 4 or not 1 <= max_links <= 500:
        raise ValueError("Crawler limits are outside the supported safe range.")
    started = time.monotonic()
    root = urlsplit(start.final_url)
    origin = urlunsplit((root.scheme, root.netloc, "", "", ""))
    allowed_host = (root.hostname or "").lower()
    robots_url = origin + "/robots.txt"
    robots = urllib.robotparser.RobotFileParser()
    robots_status: int | None = None
    robots_error = ""
    try:
        robots_response = fetch(robots_url)
        robots_status = robots_response.status_code
        robots.parse(robots_response.text.splitlines() if robots_status == 200 else [])
    except FetchError as exc:
        robots.parse([])
        robots_error = str(exc)

    queue = deque([(start.final_url, start.html, 0)])
    seen_pages = {_url_key(start.final_url)}
    pages = [_page_record(start.final_url, start.status_code, start.html)]
    records: dict[str, dict[str, Any]] = {}
    external: set[str] = set()

    while queue and len(records) < max_links:
        page_url, html, depth = queue.popleft()
        for link in discover(html, page_url):
            if len(records) >= max_links:
                break
            resolved = str(link.get("resolved_url") or "")
            try:
                parts = urlsplit(resolved)
            except ValueError:
                continue
            if parts.scheme.lower() not in {"http", "https"} or not parts.hostname:
                continue
            if parts.hostname.lower() != allowed_host:
                external.add(_url_key(resolved))
                continue
            base, fragment = urldefrag(resolved)
            page_key = _url_key(base)
            record_key = f"{page_key}#{fragment}" if fragment else page_key
            if record_key in records:
                records[record_key]["occurrences"] += 1
                continue
            record = {
                "origin_url": page_url,
                "href": link.get("href"),
                "resolved_url": base,
                "link_text": link.get("text"),
                "selector": link.get("selector"),
                "element_html": link.get("element_html"),
                "fragment": fragment or None,
                "discovered_by": link.get("discovered_by"),
                "method": "GET",
                "occurrences": 1,
                "state": "not_tested",
                "limitation": "",
            }
            records[record_key] = record
            if fragment and page_key == _url_key(page_url):
                exists = _fragment_exists(html, fragment)
                record.update(
                    state="valid" if exists else "broken",
                    status_code=200,
                    final_url=page_url,
                    limitation="" if exists else "fragment_missing",
                )
                continue
            if time.monotonic() - started >= time_budget_seconds:
                record["limitation"] = "time_budget"
                continue
            if robots_status == 200 and not robots.can_fetch(USER_AGENT, base):
                record["limitation"] = "blocked_by_robots"
                continue
            try:
                response = fetch(base)
            except FetchError as exc:
                record["limitation"] = str(exc)
                continue
            record.update(
                status_code=response.status_code,
                final_url=response.final_url,
                redirects=list(response.redirects),
                content_type=response.content_type,
            )
            if response.status_code >= 400:
                record["state"] = "broken"
            elif fragment and response.content_type in HTML_TYPES:
                record["state"] = "valid" if _fragment_exists(response.text, fragment) else "broken"
                if record["state"] == "broken":
                    record["limitation"] = "fragment_missing"
            elif response.redirects:
                record["state"] = "needs_review"
            else:
                record["state"] = "valid"
            if (depth < max_depth and 200 <= response.status_code < 300
                    and response.content_type in HTML_TYPES
                    and page_key not in seen_pages and len(seen_pages) < max_pages):
                seen_pages.add(page_key)
                seen_pages.add(_url_key(response.final_url))
                pages.append(_page_record(response.final_url, response.status_code, response.text))
                queue.append((response.final_url, response.text, depth + 1))

    links = list(records.values())
    summary = {
        "discovered": len(links),
        "tested": sum(item["state"] != "not_tested" for item in links),
        "valid": sum(item["state"] == "valid" for item in links),
        "broken": sum(item["state"] == "broken" for item in links),
        "needs_review": sum(item["state"] == "needs_review" for item in links),
        "not_tested": sum(item["state"] == "not_tested" for item in links),
        "out_of_scope": len(external),
        "pages_crawled": len(pages),
    }
    return {
        "status": "completed" if not summary["not_tested"] else "limited",
        "adapter": "scrapling.Selector",
        "transport": "pagecheck_safe_get",
        "allowed_domains": [allowed_host],
        "robots": {"url": robots_url, "status_code": robots_status,
                   "obeyed": True, "error": robots_error or None},
        "limits": {"max_pages": max_pages, "max_depth": max_depth,
                   "max_links": max_links, "time_budget_seconds": time_budget_seconds,
                   "concurrency": 1},
        "summary": summary,
        "pages": pages,
        "links": links,
        "checks": [_check(index, record) for index, record in enumerate(links, 1)],
        "limitations": [
            "Only same-host HTTP(S) links are fetched; external links are out of scope.",
            "Every discovered same-host link is verified when time and robots allow; page and depth limits only bound further discovery.",
            "The crawler is sequential, GET-only, robots-aware and bounded by pages, depth, links and time.",
        ],
    }
