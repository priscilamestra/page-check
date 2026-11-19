"""Agrega verificações estruturais de aquisição, sem rede e sem alterar dados."""
from __future__ import annotations

from collections import Counter

from pagecheck.audits.forms.rules import inspect_forms
from pagecheck.audits.navigation.rules import inspect_navigation
from pagecheck.audits.tracking.rules import inspect_tracking


def _collapse_link_inventory(checks: list[dict]) -> list[dict]:
    """Keep unvisited links as one coverage limit, not one fake check per link."""
    inventory = [item for item in checks
                 if item.get("status") == "not_verified"
                 and str(item.get("check_id") or "").startswith(("NAV_LINK_", "NAV_CTA_"))]
    if not inventory:
        return checks
    first = min(checks.index(item) for item in inventory)
    remaining = [item for item in checks if item not in inventory]
    remaining.insert(first, {
        "check_id": "NAV_DESTINATION_COVERAGE",
        "module": "navigation",
        "status": "not_verified",
        "severity": "info",
        "title": "Link destinations inventoried; availability not tested",
        "team": "Frontend / Growth",
        "evidence": {
            "count": len(inventory),
            "items": [item.get("evidence") or {} for item in inventory],
        },
        "recommendation": (
            "The live audit does not crawl every destination. This is one coverage limit, "
            "not one failure per link."
        ),
    })
    return remaining


def audit_conversion_html(html: str, page_url: str, *, niche: str = "",
                          objective: str = "leads") -> dict:
    """Não gera score: cobertura e pesos serão consolidados na Etapa 15."""
    if objective not in {"leads", "meetings", "sales", "signup", "organic_traffic"}:
        raise ValueError(f"Objetivo desconhecido: {objective!r}")
    if not isinstance(html, str) or not isinstance(page_url, str):
        raise TypeError("HTML e URL devem ser texto.")
    checks = (_collapse_link_inventory(inspect_navigation(html, page_url)) +
              inspect_forms(html, page_url, objective=objective) +
              inspect_tracking(html, page_url))
    counts = Counter(item["status"] for item in checks)
    return {
        "page_url": page_url, "niche": niche, "objective": objective,
        "source": "html_observed", "score": None,
        "counts": {status: counts[status] for status in
                   ("passed", "failed", "warning", "not_verified", "not_applicable")},
        "checks": checks,
        "limitations": [
            "Nenhuma URL de destino foi consultada nesta etapa.",
            "Nenhum CTA foi clicado e nenhum formulário foi enviado.",
            "A presença de tags não comprova disparo de eventos ou conversões.",
            "Eventos adicionados por JavaScript podem não aparecer no HTML fornecido.",
        ],
    }
