"""Inspeção passiva de UTMs e presença de scripts; não confirma eventos/conversões."""
from __future__ import annotations

from urllib.parse import parse_qs, urlsplit

from bs4 import BeautifulSoup

_REQUIRED_UTMS = ("utm_source", "utm_medium", "utm_campaign")
_TAG_HOST_HINTS = {
    "Google Tag Manager": ("googletagmanager.com/gtm.js", "googletagmanager.com/gtag/js"),
    "Google Analytics": ("google-analytics.com/analytics.js",),
    "Meta Pixel": ("connect.facebook.net/",),
    "Microsoft Clarity": ("clarity.ms/tag/",),
    "Plausible": ("plausible.io/js/",),
}


def _finding(rule: str, status: str, title: str, *, evidence: dict,
             severity: str = "info", recommendation: str = "") -> dict:
    return {
        "check_id": rule, "module": "tracking", "status": status,
        "severity": severity, "title": title, "team": "Growth / Tracking",
        "evidence": evidence, "recommendation": recommendation,
    }


def inspect_tracking(html: str, page_url: str) -> list[dict]:
    parsed = urlsplit(page_url)
    query = parse_qs(parsed.query, keep_blank_values=True)
    utm_keys = sorted(key for key in query if key.lower().startswith("utm_"))
    missing = [key for key in _REQUIRED_UTMS if not any(v.strip() for v in query.get(key, []))]
    results = []
    if not utm_keys:
        results.append(_finding("TRACK_UTM", "not_applicable",
            "Sem UTMs na URL informada", evidence={"present": [], "missing": list(_REQUIRED_UTMS)},
            recommendation="Para campanhas, informe uma URL com UTMs para validar sua estrutura."))
    else:
        results.append(_finding("TRACK_UTM", "warning" if missing else "passed",
            "Parâmetros UTM incompletos" if missing else "Parâmetros UTM preenchidos",
            evidence={"present": utm_keys, "missing": missing},
            severity="medium" if missing else "info",
            recommendation="Preencher utm_source, utm_medium e utm_campaign de acordo com o padrão da campanha."
            if missing else ""))
    soup = BeautifulSoup(html, "html.parser")
    sources = [str(t.get("src") or "").lower() for t in soup.find_all("script")]
    found = [name for name, needles in _TAG_HOST_HINTS.items()
             if any(needle in src for needle in needles for src in sources)]
    results.append(_finding("TRACK_TAG_PRESENCE", "not_verified",
        "Tags identificadas; disparo e entrega não verificados" if found else
        "Nenhuma das tags reconhecidas foi identificada no HTML",
        evidence={"tags_observed": found, "script_count": len(sources)},
        recommendation="Confirmar disparo de eventos e recebimento no analytics em ambiente autorizado."))
    return results
