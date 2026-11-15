"""Converte saída JSON do detector Impeccable em achados Page Check."""
from __future__ import annotations

from pagecheck.integrations.engine_result import EngineOutputError, result


def normalize_impeccable(payload: object) -> dict:
    # A CLI documenta uma lista JSON; algumas versões encapsulam em 'findings'.
    if isinstance(payload, list):
        records = payload
    elif isinstance(payload, dict) and isinstance(payload.get("findings"), list):
        records = payload["findings"]
    else:
        raise EngineOutputError("Impeccable não retornou lista de achados válida.")
    findings = []
    for index, row in enumerate(records):
        if not isinstance(row, dict):
            raise EngineOutputError("Impeccable retornou achado inválido.")
        # Detector versions have used both camelCase and snake_case keys.
        # Only accept explicit rule identifiers. Never manufacture a rule ID
        # from the message, severity, file path or array position.
        rule = (row.get("ruleId") or row.get("rule_id") or row.get("rule")
                or row.get("id") or row.get("checkId") or row.get("check_id"))
        if isinstance(rule, dict):
            rule = (rule.get("id") or rule.get("ruleId") or rule.get("rule_id")
                    or rule.get("key"))
        if not isinstance(rule, str) or not rule.strip():
            raise EngineOutputError("Impeccable retornou achado sem identificador de regra.")
        level = str(row.get("severity") or row.get("level") or "warning").lower()
        severity = {"error": "high", "critical": "critical", "warning": "medium",
                    "info": "low", "advisory": "low"}.get(level, "medium")
        findings.append({
            "id": f"impeccable:{rule}:{index}", "source": "impeccable",
            "module": "layout", "status": "warning", "severity": severity,
            "title": str(row.get("message") or row.get("title") or rule),
            "description": str(row.get("description") or ""),
            "evidence": {"rule_id": rule, "file": row.get("file"),
                         "line": row.get("line"), "selector": row.get("selector")},
            "owner": "Design / Frontend",
        })
    return result("impeccable", findings=findings, metrics={"findings": len(findings)},
                  limitations=["Alertas de design podem ser intencionais; requerem revisão."])
