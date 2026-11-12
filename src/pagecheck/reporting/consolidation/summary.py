"""Métricas somente de resultados observados, sem score global inventado."""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

STATUSES = ("passed", "failed", "warning", "not_verified", "not_applicable")
SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}


def summarize_checks(checks: list[dict[str, Any]]) -> dict[str, Any]:
    counter = Counter(c["status"] for c in checks)
    applicable = len(checks) - counter["not_applicable"]
    executed = sum(counter[key] for key in ("passed", "failed", "warning"))
    # Cobertura de checks conhecidos. NÃO mede cobertura das ferramentas inteiras.
    return {
        "counts": {key: counter[key] for key in STATUSES},
        "check_coverage": {
            "executed": executed,
            "applicable": applicable,
            "ratio": round(executed / applicable, 3) if applicable else None,
            "meaning": "Somente checks recebidos; não mede abrangência da auditoria inteira.",
        },
    }


def priority_findings(checks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        (c for c in checks if c["status"] in {"failed", "warning"}),
        key=lambda c: (SEVERITY_ORDER.get(c["severity"], 5), c["id"]),
    )


def group_actions(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for finding in findings:
        groups[finding["team"]].append({
            "finding_id": finding["id"],
            "priority": finding["severity"],
            "title": finding["title"],
            "action": finding["recommendation"],
        })
    return [
        {"team": team, "count": len(groups[team]), "actions": groups[team]}
        for team in sorted(groups)
    ]
