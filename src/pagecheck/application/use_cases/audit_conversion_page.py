"""Agrega verificações estruturais de aquisição, sem rede e sem alterar dados."""
from __future__ import annotations

from collections import Counter

from pagecheck.audits.forms.rules import inspect_forms
from pagecheck.audits.navigation.rules import inspect_navigation
from pagecheck.audits.tracking.rules import inspect_tracking


def audit_conversion_html(html: str, page_url: str, *, niche: str = "",
                          objective: str = "leads") -> dict:
    """Não gera score: cobertura e pesos serão consolidados na Etapa 15."""
    if objective not in {"leads", "meetings", "sales", "signup", "organic_traffic"}:
        raise ValueError(f"Objetivo desconhecido: {objective!r}")
    if not isinstance(html, str) or not isinstance(page_url, str):
        raise TypeError("HTML e URL devem ser texto.")
    checks = (inspect_navigation(html, page_url) +
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
