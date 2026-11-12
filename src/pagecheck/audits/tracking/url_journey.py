"""Regras passivas para parâmetros de campanha e cadeia de redirecionamentos.

Não consulta Google Ads/GA4, não acessa rede e não supõe atribuição de conversões.
"""
from __future__ import annotations

from collections import defaultdict
from urllib.parse import parse_qsl, urlsplit

UTMS = ("utm_source", "utm_medium", "utm_campaign")
CLICK_IDS = ("gclid", "gbraid", "wbraid", "fbclid", "msclkid", "ttclid")


def _pairs(url: str) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for key, value in parse_qsl(urlsplit(url).query, keep_blank_values=True):
        grouped[key.lower()].append(value)
    return dict(grouped)


def _check(code: str, status: str, title: str, evidence: dict,
           severity: str = "info", recommendation: str = "") -> dict:
    return {
        "check_id": code, "module": "tracking", "status": status,
        "severity": severity, "title": title, "team": "Growth / Tracking",
        "evidence": evidence, "recommendation": recommendation,
    }


def inspect_url_journey(requested_url: str, final_url: str,
                        redirects: list[str] | tuple[str, ...] = ()) -> list[dict]:
    """Avalia a URL de entrada e a final; não valida conversões ou eventos reais.

    Valores de IDs de clique e UTMs nunca são incluídos no relatório.
    A ausência de UTM em uma URL simples não é um erro.
    """
    incoming = _pairs(requested_url)
    outgoing = _pairs(final_url)
    keys = sorted(k for k in incoming if k.startswith("utm_"))
    checks: list[dict] = []
    if not keys:
        checks.append(_check("URL_UTM_STRUCTURE", "not_applicable",
                             "A URL informada não contém UTMs",
                             {"utm_keys": [], "note": "UTMs não são obrigatórias para todas as páginas."}))
    else:
        empty = sorted(k for k in keys if any(not value.strip() for value in incoming[k]))
        missing = [name for name in UTMS if not any(value.strip() for value in incoming.get(name, []))]
        conflicted = sorted(k for k in keys if len(set(incoming[k])) > 1)
        status = "warning" if empty or missing or conflicted else "passed"
        checks.append(_check("URL_UTM_STRUCTURE", status,
                             "Revisar parâmetros UTM" if status == "warning" else "UTMs preenchidas",
                             {"utm_keys": keys, "empty_keys": empty,
                              "missing_recommended": missing, "conflicting_duplicates": conflicted},
                             "medium" if status == "warning" else "info",
                             "Revisar campos vazios, duplicados e o padrão da campanha; não existe obrigatoriedade universal de UTMs."
                             if status == "warning" else ""))

    tracked = sorted(k for k in incoming if k.startswith("utm_") or k in CLICK_IDS)
    if not tracked:
        checks.append(_check("URL_REDIRECT_PARAMETERS", "not_applicable",
                             "Sem parâmetros de campanha para comparar no redirecionamento",
                             {"redirects": len(redirects)}))
    elif not redirects and requested_url == final_url:
        checks.append(_check("URL_REDIRECT_PARAMETERS", "not_applicable",
                             "Sem redirecionamento observado",
                             {"tracked_keys": tracked, "redirects": 0}))
    else:
        dropped = sorted(k for k in tracked if not outgoing.get(k) or
                         not any(v in outgoing[k] for v in incoming[k] if v))
        checks.append(_check("URL_REDIRECT_PARAMETERS", "warning" if dropped else "passed",
                             "Parâmetros mudaram durante o redirecionamento" if dropped else
                             "Parâmetros de campanha preservados no destino",
                             {"tracked_keys": tracked, "lost_or_changed_keys": dropped,
                              "redirects": len(redirects)},
                             "medium" if dropped else "info",
                             "Revisar o redirecionamento e a estratégia de atribuição; perder um parâmetro não prova perda de conversões."
                             if dropped else ""))
    return checks
