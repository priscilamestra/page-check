"""Auditoria determinística sobre a saída COMPLETA de parse_html().

Não aceita prévias truncadas do endpoint /v1/pages/inspect. Não consulta SERPs,
não prediz ranking do Google e não acessa a rede.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlsplit

RULESET_VERSION = "seo-1.0.0"
OBJECTIVES = frozenset({"leads", "meetings", "sales", "signup", "organic_traffic"})

# O score é uma convenção de diagnóstico do Page Check, não um score do Google.
WEIGHTS = {
    "SEO_TITLE": 3,
    "SEO_DESCRIPTION": 2,
    "SEO_H1": 3,
    "SEO_HEADING_ORDER": 1,
    "SEO_CANONICAL": 2,
    "SEO_NOINDEX": 4,
    "SEO_IMAGE_ALT": 1,
}


def _check(
    check_id: str,
    status: str,
    *,
    url: str,
    observed: Any,
    title: str,
    severity: str = "info",
    recommendation: str = "",
) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "module": "seo",
        "status": status,
        "severity": severity,
        "title": title,
        "weight": WEIGHTS[check_id],
        "target_url": url,
        "team": "SEO / Conteúdo",
        "evidence": {"source": "beautifulsoup", "observed_value": observed},
        "recommendation": recommendation,
    }


def _unavailable(check_id: str, url: str, title: str) -> dict[str, Any]:
    return _check(
        check_id, "not_verified", url=url, observed=None, title=title,
        recommendation="O dado necessário não foi fornecido pelo parser.",
    )


def _absolute_http_url(value: str) -> bool:
    try:
        p = urlsplit(value)
        return p.scheme.lower() in {"http", "https"} and bool(p.hostname)
    except ValueError:
        return False


def audit_seo(extracted: Mapping[str, Any], *, objective: str = "leads") -> dict[str, Any]:
    """Avalia metadados e estrutura de HTML completo, sem rede ou LLM.

    `extracted` deve ser a saída completa de `parse_html`, não uma prévia
    truncada. Avisos são heurísticos e ganham metade do peso na nota.
    Regras não verificadas não recebem pontos e reduzem a cobertura.
    """
    if objective not in OBJECTIVES:
        raise ValueError(f"Objetivo desconhecido: {objective!r}")
    if not isinstance(extracted, Mapping):
        raise TypeError("extracted deve ser um mapeamento produzido por parse_html")

    url = str(extracted.get("page_url") or "")
    checks: list[dict[str, Any]] = []

    if "title" not in extracted:
        checks.append(_unavailable("SEO_TITLE", url, "Verificar title"))
    else:
        title = str(extracted.get("title") or "").strip()
        checks.append(_check(
            "SEO_TITLE", "passed" if title else "failed", url=url,
            observed=title or None, title="Title presente",
            severity="info" if title else "medium",
            recommendation="Adicionar um <title> descritivo." if not title else "",
        ))

    if "meta_description" not in extracted:
        checks.append(_unavailable("SEO_DESCRIPTION", url, "Verificar meta description"))
    else:
        description = str(extracted.get("meta_description") or "").strip()
        checks.append(_check(
            "SEO_DESCRIPTION", "passed" if description else "failed", url=url,
            observed=description or None, title="Meta description presente",
            severity="info" if description else "medium",
            recommendation=(
                "Adicionar uma meta description útil para descrever a página."
                if not description else ""
            ),
        ))

    headings = extracted.get("headings")
    if not isinstance(headings, list):
        checks.append(_unavailable("SEO_H1", url, "Verificar H1"))
        checks.append(_unavailable("SEO_HEADING_ORDER", url, "Verificar ordem dos headings"))
    else:
        valid = [h for h in headings if isinstance(h, dict)]
        h1s = [h for h in valid if str(h.get("level", "")).lower() == "h1"
               and str(h.get("text") or "").strip()]
        if not h1s:
            checks.append(_check(
                "SEO_H1", "failed", url=url, observed=0, title="H1 encontrado",
                severity="medium", recommendation="Definir um H1 textual para o conteúdo principal.",
            ))
        elif len(h1s) > 1:
            checks.append(_check(
                "SEO_H1", "warning", url=url, observed=len(h1s),
                title="Mais de um H1", severity="low",
                recommendation="Revisar se a estrutura de títulos está clara; vários H1 não são automaticamente erro.",
            ))
        else:
            checks.append(_check(
                "SEO_H1", "passed", url=url, observed=1, title="H1 encontrado",
            ))

        levels = [int(str(h.get("level", "h0"))[1:]) for h in valid
                  if str(h.get("level", "")).lower() in {"h1", "h2", "h3"}]
        if not levels:
            checks.append(_check(
                "SEO_HEADING_ORDER", "not_applicable", url=url, observed=[],
                title="Ordem dos headings", recommendation="",
            ))
        else:
            jumps = [(a, b) for a, b in zip(levels, levels[1:]) if b > a + 1]
            checks.append(_check(
                "SEO_HEADING_ORDER", "warning" if jumps else "passed", url=url,
                observed={"levels": levels, "jumps": jumps},
                title="Hierarquia dos headings", severity="low" if jumps else "info",
                recommendation=(
                    "Revisar saltos de nível entre headings; é um alerta estrutural, não fator isolado de ranking."
                    if jumps else ""
                ),
            ))

    if "canonical" not in extracted:
        checks.append(_unavailable("SEO_CANONICAL", url, "Verificar canonical"))
    else:
        canonical = extracted.get("canonical")
        if canonical is None or not str(canonical).strip():
            checks.append(_check(
                "SEO_CANONICAL", "warning", url=url, observed=None,
                title="Canonical não declarada", severity="low",
                recommendation="Avaliar uma URL canônica para controlar duplicação, quando aplicável.",
            ))
        elif not _absolute_http_url(str(canonical)):
            checks.append(_check(
                "SEO_CANONICAL", "failed", url=url, observed=str(canonical),
                title="Canonical inválida", severity="medium",
                recommendation="Informar URL canônica HTTP(S) absoluta e válida.",
            ))
        else:
            checks.append(_check(
                "SEO_CANONICAL", "passed", url=url, observed=str(canonical),
                title="Canonical declarada",
            ))

    if objective != "organic_traffic":
        checks.append(_check(
            "SEO_NOINDEX", "not_applicable", url=url,
            observed=extracted.get("meta_robots"), title="Noindex para tráfego orgânico",
        ))
    elif "meta_robots" not in extracted:
        checks.append(_unavailable("SEO_NOINDEX", url, "Verificar meta robots"))
    else:
        robots = str(extracted.get("meta_robots") or "")
        has_noindex = bool(re.search(r"(?:^|[,\s])noindex(?:$|[,\s])", robots, re.I))
        checks.append(_check(
            "SEO_NOINDEX", "failed" if has_noindex else "passed", url=url,
            observed=robots or None, title="Diretiva HTML noindex",
            severity="high" if has_noindex else "info",
            recommendation=(
                "Revisar a meta robots noindex para esta página destinada ao tráfego orgânico."
                if has_noindex else ""
            ),
        ))

    images = extracted.get("images")
    if not isinstance(images, list):
        checks.append(_unavailable("SEO_IMAGE_ALT", url, "Verificar textos alternativos"))
    elif not images:
        checks.append(_check(
            "SEO_IMAGE_ALT", "not_applicable", url=url, observed=0,
            title="Atributo alt das imagens",
        ))
    else:
        missing = [img.get("src") or img.get("data_src") for img in images
                   if isinstance(img, dict) and img.get("alt") is None]
        checks.append(_check(
            "SEO_IMAGE_ALT", "warning" if missing else "passed", url=url,
            observed={"count": len(images), "missing_alt_sources": missing[:20]},
            title="Atributo alt das imagens", severity="low" if missing else "info",
            recommendation=(
                "Revisar imagens sem atributo alt; imagens decorativas podem usar alt vazio."
                if missing else ""
            ),
        ))

    applicable = [c for c in checks if c["status"] != "not_applicable"]
    executed = [c for c in applicable if c["status"] != "not_verified"]
    denominator = sum(c["weight"] for c in executed)
    factor = {"passed": 1.0, "warning": 0.5, "failed": 0.0}
    weighted_points = sum(c["weight"] * factor[c["status"]] for c in executed)
    score = round(100 * weighted_points / denominator, 1) if denominator else None
    coverage = round(len(executed) / len(applicable), 3) if applicable else 1.0

    return {
        "module": "seo",
        "ruleset_version": RULESET_VERSION,
        "objective": objective,
        "score": score,
        "coverage": coverage,
        "partial_score": score is not None and coverage < 0.70,
        "checks_executed": len(executed),
        "checks_applicable": len(applicable),
        "checks": checks,
        "findings": [c for c in checks if c["status"] in {"failed", "warning"}],
    }
