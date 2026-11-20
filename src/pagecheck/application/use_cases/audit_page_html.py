"""Auditoria observável: HTML seguro, motores estáticos e captura visual opcional.

Não clica, não faz POST e não testa HTTP de links externos.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from pagecheck.acquisition.http.fetcher import FetchedPage, fetch_html
from pagecheck.acquisition.http.parser import parse_html
from pagecheck.application.use_cases.audit_conversion_page import audit_conversion_html
from pagecheck.application.use_cases.consolidate_audit import consolidate_audit
from pagecheck.audits.seo.content_guidance import (
    LANGUAGES,
    inspect_content_guidance,
    normalize_keywords,
)
from pagecheck.audits.seo.rules import audit_seo
from pagecheck.audits.seo.site_rules import audit_crawled_pages
from pagecheck.audits.tracking.url_journey import inspect_url_journey
from pagecheck.common.security.url_validation import validate_public_url
from pagecheck.reporting.english_copy import englishize_report


def audit_page_html(url: str, *, niche: str, objective: str,
                    language: str = "en", keywords: Sequence[str] | None = None,
                    fetch: Callable[[str], FetchedPage] = fetch_html,
                    crawler: Callable[[FetchedPage], Mapping[str, Any]] | None = None,
                    visual_collector: Callable[[str], Mapping[str, Any]] | None = None,
                    external_collector: Callable[[str, str], Mapping[str, Any]] | None = None,
                    ) -> dict[str, Any]:
    """Consolida resultados observados sem indicar auditoria visual como executada."""
    validated = validate_public_url(url)
    if not isinstance(niche, str) or len(niche.strip()) < 2:
        raise ValueError("Informe um nicho válido.")
    if language not in LANGUAGES:
        raise ValueError("Choose a supported content language.")
    target_keywords = normalize_keywords(keywords)
    page = fetch(validated)
    extracted = parse_html(page.html, page.final_url)
    seo = audit_seo(extracted, objective=objective)
    guidance = inspect_content_guidance(
        page.html, extracted, language=language, niche=niche.strip(), keywords=target_keywords,
    )
    # Guidance is returned alongside structural SEO; it does not silently change
    # the original technical SEO score or pretend to query search engines.
    seo["checks"].extend(guidance["checks"])
    seo["findings"].extend(row for row in guidance["checks"]
                           if row["status"] in {"failed", "warning"})
    conversion = audit_conversion_html(page.html, page.final_url,
                                       niche=niche.strip(), objective=objective)
    crawl_result: Mapping[str, Any] | None = None
    if crawler is not None:
        try:
            candidate = crawler(page)
            if not isinstance(candidate, Mapping):
                raise TypeError("Crawler must return a mapping.")
            crawl_result = candidate
            crawl_checks = candidate.get("checks")
            if isinstance(crawl_checks, list):
                conversion["checks"].extend(
                    row for row in crawl_checks if isinstance(row, Mapping)
                )
            pages = candidate.get("pages")
            if isinstance(pages, list):
                site_checks = audit_crawled_pages(
                    [dict(row) for row in pages if isinstance(row, Mapping)]
                )
                seo["checks"].extend(site_checks)
                seo["findings"].extend(
                    row for row in site_checks if row["status"] in {"failed", "warning"}
                )
        except Exception as exc:  # noqa: BLE001 - limited crawl must not erase the page audit.
            crawl_result = {
                "status": "limited", "checks": [], "pages": [], "links": [],
                "summary": {"discovered": 0, "tested": 0, "valid": 0, "broken": 0,
                            "needs_review": 0, "not_tested": 0, "out_of_scope": 0,
                            "pages_crawled": 0},
                "limitations": [f"Limited crawl unavailable ({type(exc).__name__})."],
            }
    # A regra legada TRACK_UTM olhava apenas a URL final e poderia contradizer
    # o diagnóstico da URL de entrada após um redirecionamento.
    conversion["checks"] = [
        item for item in conversion["checks"] if item.get("check_id") != "TRACK_UTM"
    ]
    conversion["checks"].extend(inspect_url_journey(
        validated, page.final_url, page.redirects,
    ))
    counts = Counter(item["status"] for item in conversion["checks"])
    conversion["counts"] = {status: counts[status] for status in
                            ("passed", "failed", "warning", "not_verified", "not_applicable")}
    visual_capture: Mapping[str, Any] | None = None
    if visual_collector is not None:
        try:
            visual_capture = visual_collector(page.final_url)
        except Exception as exc:  # noqa: BLE001 - visual capture is optional evidence.
            visual_capture = {
                "visuals": {}, "status": "not_verified",
                "errors": {"browser": f"Browser unavailable ({type(exc).__name__})."},
                "mode": "guarded_javascript_get_only",
            }
    external_result: Mapping[str, Any] | None = None
    if external_collector is not None:
        try:
            candidate = external_collector(page.html, page.final_url)
            if not isinstance(candidate, Mapping):
                raise TypeError("External collector must return a mapping.")
            external_result = candidate
        except Exception as exc:  # noqa: BLE001 - external engines cannot abort the audit.
            from pagecheck.application.use_cases.external_engines import combine_engines
            external_result = combine_engines({})
            external_result["execution_error"] = type(exc).__name__
    report = consolidate_audit(
        requested_url=validated,
        final_url=page.final_url,
        niche=niche.strip(), objective=objective,
        seo=seo, conversion=conversion,
        visuals=visual_capture.get("visuals") if visual_capture is not None else None,
        external=external_result,
    )
    if external_result is not None:
        report["external_capture"] = {
            "mode": "opt_in_sanitized_static_html",
            "status": external_result.get("status", "not_verified"),
            "limitations": [
                (
                    "External checks analyze a sanitized snapshot from the same safe HTML fetch. "
                    "They do not validate runtime performance "
                    "or the original page's full visual design."
                )
            ],
        }
    if visual_capture is not None:
        report["visual_capture"] = {
            key: value for key, value in visual_capture.items() if key != "visuals"
        }
    report["audit_context"] = {"language": language, "keywords": target_keywords}
    report["seo_content_guidance"] = {
        "language": guidance["language"], "niche": guidance["niche"],
        "keywords": guidance["keywords"],
        "relevance_candidates": guidance["relevance_candidates"],
        "limitations": guidance["limitations"],
    }
    if crawl_result is not None:
        report["link_audit"] = dict(crawl_result)
    report["http"] = {"status_code": page.status_code,
                      "redirect_count": len(page.redirects),
                      "redirects": list(page.redirects)}
    return englishize_report(report)
