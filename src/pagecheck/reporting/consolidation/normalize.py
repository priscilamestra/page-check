"""Adapta checks de HTML, achados visuais e motores ao mesmo contrato.

Este módulo NÃO coleta páginas, não reclassifica achados e não atribui pesos.
Os dados de origem permanecem disponíveis no campo `evidence`.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

VALID_STATUS = frozenset({"passed", "failed", "warning", "not_verified", "not_applicable"})
VALID_SEVERITY = frozenset({"critical", "high", "medium", "low", "info"})


def _text(value: object, default: str) -> str:
    return str(value).strip() if value is not None and str(value).strip() else default


def normalize_check(
    record: Mapping[str, Any], *, source: str, page_url: str,
    default_module: str, viewport: str | None = None,
) -> dict[str, Any]:
    """Uniformiza um check sem transformar `not_verified` em sucesso.

    Achados visuais não têm um `status` explícito em algumas etapas.
    O detector de imagem comprovadamente quebrada usa failed; os demais
    avisos geométricos, sem resultado explícito, recebem warning.
    """
    if not isinstance(record, Mapping):
        raise TypeError("Cada check precisa ser um objeto/mapeamento.")

    module = _text(record.get("module") or record.get("category"), default_module)
    raw_id = _text(record.get("check_id") or record.get("id"), "unknown")
    raw_status = record.get("status")
    if raw_status is None and source == "playwright":
        status = "failed" if raw_id.startswith("image-broken-") else "warning"
    else:
        status = raw_status if raw_status in VALID_STATUS else "not_verified"
    raw_severity = record.get("severity")
    severity = (raw_severity if raw_severity in VALID_SEVERITY else
                "medium" if status in {"failed", "warning"} else "info")
    evidence_value = record.get("evidence")
    if isinstance(evidence_value, Mapping):
        evidence = dict(evidence_value)
    elif evidence_value is None:
        evidence = {}
    else:
        evidence = {"observed_value": evidence_value}
    if isinstance(record.get("box"), Mapping):
        evidence["box"] = dict(record["box"])

    url = _text(record.get("target_url"), page_url)
    normalized = {
        "id": f"{source}:{viewport or 'page'}:{module}:{raw_id}",
        "check_id": raw_id,
        "source": source,
        "module": module,
        "viewport": viewport,
        "status": status,
        "severity": severity,
        "title": _text(record.get("title"), "Verificação sem título"),
        "description": _text(record.get("description"), ""),
        "recommendation": _text(record.get("recommendation") or record.get("action"), ""),
        "team": _text(record.get("team") or record.get("owner"), "Revisão técnica"),
        "target_url": url,
        "evidence": evidence,
    }
    if raw_status is not None and raw_status not in VALID_STATUS:
        normalized["evidence"]["invalid_original_status"] = str(raw_status)
    return normalized
