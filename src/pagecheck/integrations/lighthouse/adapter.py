"""Normaliza o JSON LHR do Lighthouse mantendo as notas originais."""
from __future__ import annotations

from pagecheck.integrations.engine_result import EngineOutputError, require_mapping, result

CATEGORY_NAMES = ("performance", "accessibility", "best-practices", "seo")


def normalize_lighthouse(payload: object) -> dict:
    lhr = require_mapping(payload, "Lighthouse")
    categories = require_mapping(lhr.get("categories"), "Lighthouse.categories")
    scores: dict[str, int | None] = {}
    for category in CATEGORY_NAMES:
        entry = categories.get(category)
        if not isinstance(entry, dict) or entry.get("score") is None:
            scores[category] = None
        else:
            raw = entry["score"]
            if isinstance(raw, bool) or not isinstance(raw, (int, float)) or not 0 <= raw <= 1:
                raise EngineOutputError(f"Nota Lighthouse inválida: {category}.")
            scores[category] = round(raw * 100)

    audits = lhr.get("audits", {})
    if not isinstance(audits, dict):
        raise EngineOutputError("Lighthouse.audits inválido.")
    selected = set()
    for entry in categories.values():
        if isinstance(entry, dict):
            for audit_ref in entry.get("auditRefs", []):
                if isinstance(audit_ref, dict) and isinstance(audit_ref.get("id"), str):
                    selected.add(audit_ref["id"])
    findings = []
    for audit_id in sorted(selected):
        audit = audits.get(audit_id)
        if not isinstance(audit, dict):
            continue
        score = audit.get("score")
        mode = audit.get("scoreDisplayMode")
        if (mode in {"notApplicable", "manual", "informative"} or
                isinstance(score, bool) or not isinstance(score, (int, float)) or score >= .9):
            continue
        findings.append({
            "id": f"lighthouse:{audit_id}", "source": "lighthouse", "module": "technical",
            "status": "warning" if score > .5 else "failed",
            "severity": "medium" if score > .5 else "high",
            "title": str(audit.get("title") or audit_id),
            "description": str(audit.get("description") or ""),
            "evidence": {"audit_id": audit_id, "score": score,
                         "display_value": audit.get("displayValue")},
            "owner": "Frontend / Performance",
        })
    return result(
        "lighthouse", scores=scores, findings=findings,
        metrics={"requested_url": lhr.get("requestedUrl"),
                 "final_url": lhr.get("finalUrl"), "lighthouse_version": lhr.get("lighthouseVersion")},
        limitations=["Notas do Lighthouse são próprias; não somar ao score Page Check."],
    )
