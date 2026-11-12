"""Consolida motores independentes sem inventar scores para falhas."""
from __future__ import annotations

from collections import Counter
from typing import Any

from pagecheck.integrations.engine_result import unavailable

ENGINES = ("lighthouse", "axe", "impeccable")


def combine_engines(reports: dict[str, dict[str, Any]]) -> dict:
    normalized = {}
    for name in ENGINES:
        report = reports.get(name)
        normalized[name] = (report if isinstance(report, dict) and
                            report.get("engine") == name and
                            report.get("status") in {"completed", "not_verified"}
                            else unavailable(name, "Motor não foi executado."))
    counts = Counter(r["status"] for r in normalized.values())
    return {
        "status": ("completed" if counts["completed"] == len(ENGINES)
                   else "partial" if counts["completed"] else "not_verified"),
        "engines": normalized,
        "counts": {"completed": counts["completed"], "not_verified": counts["not_verified"]},
        "notes": ["Pontuações Lighthouse são independentes do score Page Check.",
                  "Motores não executados não geram resultados positivos nem nota zero."],
    }
