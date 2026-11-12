"""Auditoria HTML observável: coleta ÚNICA para SEO, links, formulários e UTMs.

Não executa JavaScript, não clica, não faz POST e não testa HTTP de links externos.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pagecheck.acquisition.http.fetcher import FetchedPage, fetch_html
from pagecheck.acquisition.http.parser import parse_html
from pagecheck.application.use_cases.audit_conversion_page import audit_conversion_html
from pagecheck.application.use_cases.consolidate_audit import consolidate_audit
from pagecheck.audits.seo.rules import audit_seo
from pagecheck.audits.tracking.url_journey import inspect_url_journey
from pagecheck.common.security.url_validation import validate_public_url


def audit_page_html(url: str, *, niche: str, objective: str,
                    fetch: Callable[[str], FetchedPage] = fetch_html) -> dict[str, Any]:
    """Consolida resultados observados sem indicar auditoria visual como executada."""
    validated = validate_public_url(url)
    if not isinstance(niche, str) or len(niche.strip()) < 2:
        raise ValueError("Informe um nicho válido.")
    page = fetch(validated)
    extracted = parse_html(page.html, page.final_url)
    seo = audit_seo(extracted, objective=objective)
    conversion = audit_conversion_html(page.html, page.final_url,
                                       niche=niche.strip(), objective=objective)
    # A regra legada TRACK_UTM olhava apenas a URL final e poderia contradizer
    # o diagnóstico da URL de entrada após um redirecionamento.
    conversion["checks"] = [
        item for item in conversion["checks"] if item.get("check_id") != "TRACK_UTM"
    ]
    conversion["checks"].extend(inspect_url_journey(
        validated, page.final_url, page.redirects,
    ))
    report = consolidate_audit(
        requested_url=validated,
        final_url=page.final_url,
        niche=niche.strip(), objective=objective,
        seo=seo, conversion=conversion,
    )
    report["http"] = {"status_code": page.status_code,
                      "redirect_count": len(page.redirects),
                      "redirects": list(page.redirects)}
    report["limitations"].extend([
        "Auditoria HTML executada; JavaScript, screenshots e motores externos não foram executados neste fluxo.",
        "Destinos dos links e checkouts foram identificados, mas ainda não consultados nem clicados.",
    ])
    return report
