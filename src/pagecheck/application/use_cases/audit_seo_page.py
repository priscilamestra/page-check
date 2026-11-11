"""Orquestra a auditoria SEO usando HTML completo, sem acoplamento à API/UI."""

from collections.abc import Callable
from typing import Any

from pagecheck.acquisition.http.fetcher import FetchedPage, fetch_html
from pagecheck.acquisition.http.parser import parse_html
from pagecheck.audits.seo.rules import audit_seo
from pagecheck.common.security.url_validation import validate_public_url


def audit_seo_page(
    url: str,
    *,
    niche: str,
    objective: str,
    fetch: Callable[[str], FetchedPage] = fetch_html,
) -> dict[str, Any]:
    """Obtém a página uma vez, analisa HTML completo e aplica regras SEO.

    `fetch` é injetável nos testes. Nicho é metadado de contexto, ainda
    não é utilizado para inferir relevância temática nem ranking do Google.
    """
    validated_url = validate_public_url(url)
    page = fetch(validated_url)
    extracted = parse_html(page.html, page.final_url)
    evaluated = audit_seo(extracted, objective=objective)

    return {
        "requested_url": validated_url,
        "final_url": page.final_url,
        "status_code": page.status_code,
        "redirects": list(page.redirects),
        "niche": niche,
        **evaluated,
    }
