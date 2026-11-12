"""Normalização das violações produzidas pelo motor axe-core."""
from __future__ import annotations

from pagecheck.integrations.engine_result import EngineOutputError, require_mapping, result

SEVERITY = {"critical": "critical", "serious": "high", "moderate": "medium", "minor": "low"}


def normalize_axe(payload: object) -> dict:
    data = require_mapping(payload, "axe-core")
    violations = data.get("violations")
    if not isinstance(violations, list):
        raise EngineOutputError("axe-core.violations deve ser uma lista.")
    findings = []
    for row in violations:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str):
            raise EngineOutputError("Violação axe-core malformada.")
        nodes = row.get("nodes", [])
        if not isinstance(nodes, list):
            raise EngineOutputError("axe-core.nodes inválido.")
        findings.append({
            "id": "axe:" + row["id"], "source": "axe", "module": "accessibility",
            "status": "failed", "severity": SEVERITY.get(row.get("impact"), "medium"),
            "title": str(row.get("help") or row["id"]),
            "description": str(row.get("description") or ""),
            "evidence": {"rule_id": row["id"], "help_url": row.get("helpUrl"),
                         "affected_nodes": len(nodes),
                         "selectors": [node.get("target", []) for node in nodes[:10]
                                       if isinstance(node, dict)]},
            "owner": "Frontend / Acessibilidade",
        })
    incomplete = data.get("incomplete", [])
    return result(
        "axe", findings=findings,
        metrics={"violations": len(findings),
                 "incomplete_rules": len(incomplete) if isinstance(incomplete, list) else None,
                 "passes": len(data["passes"]) if isinstance(data.get("passes"), list) else None},
        limitations=["Testes automáticos de acessibilidade não substituem revisão humana."],
    )
