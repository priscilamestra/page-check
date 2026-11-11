"""Orquestra extração HTML sem conhecer FastAPI ou Streamlit."""

from collections.abc import Callable
from typing import Any

from pagecheck.acquisition.http.fetcher import FetchedPage, fetch_html
from pagecheck.acquisition.http.parser import parse_html
from pagecheck.common.security.url_validation import validate_public_url

MAX_HEADINGS_PREVIEW = 30
MAX_LINKS_PREVIEW = 25
MAX_IMAGES_PREVIEW = 25


def inspect_page(
    url: str,
    *,
    fetch: Callable[[str], FetchedPage] = fetch_html,
) -> dict[str, Any]:
    """Inspeciona uma página e devolve fatos, sem emitir notas ou recomendações.

    O fetcher pode ser injetado para testes sem qualquer acesso à internet.
    """
    validated_url = validate_public_url(url)
    page = fetch(validated_url)
    extracted = parse_html(page.html, page.final_url)

    headings = extracted["headings"]
    links = extracted["links"]
    images = extracted["images"]

    return {
        "requested_url": validated_url,
        "final_url": page.final_url,
        "status_code": page.status_code,
        "redirects": list(page.redirects),
        "title": extracted["title"],
        "meta_description": extracted["meta_description"],
        "meta_robots": extracted["meta_robots"],
        "canonical": extracted["canonical"],
        "headings_count": len(headings),
        "headings": headings[:MAX_HEADINGS_PREVIEW],
        "links_count": len(links),
        "links_preview": links[:MAX_LINKS_PREVIEW],
        "images_count": len(images),
        "images_preview": images[:MAX_IMAGES_PREVIEW],
        "previews_truncated": {
            "headings": len(headings) > MAX_HEADINGS_PREVIEW,
            "links": len(links) > MAX_LINKS_PREVIEW,
            "images": len(images) > MAX_IMAGES_PREVIEW,
        },
        "audit_scored": False,
    }
