"""Stage 19D: bounded team task explorer, without hiding underlying actions."""
from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

PRIORITIES = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}


def team_tasks(report: Mapping[str, Any], *,
               team_label: Callable[[object], str] | None = None,
               describe: Callable[[dict[str, Any]], tuple[str, str | None]] | None = None,
               ) -> list[dict[str, Any]]:
    groups = report.get("actions_by_team") or []
    if not isinstance(groups, list):
        return []
    result: list[dict[str, Any]] = []
    for group_id, group in enumerate(groups):
        if not isinstance(group, Mapping):
            continue
        team = team_label(group.get("team")) if team_label else str(group.get("team") or "Other")
        actions = group.get("actions") or []
        if not isinstance(actions, list):
            continue
        for task_index, task in enumerate(actions):
            if not isinstance(task, dict):
                continue
            title, suggestion = (describe(task) if describe else (
                str(task.get("title") or "Task"),
                str(task.get("action") or task.get("recommendation") or "")))
            # A few older reports store action text in `action`, not `recommendation`.
            if not suggestion:
                suggestion = str(task.get("action") or task.get("recommendation") or "")
            severity = str(task.get("priority") or task.get("severity") or "info").lower()
            if severity not in PRIORITIES:
                severity = "info"
            result.append({
                "index": len(result), "group_index": group_id, "task_index": task_index,
                "team": str(team), "title": str(title or "Task"),
                "recommendation": str(suggestion), "priority": severity,
                "evidence": task.get("evidence") or {},
                "finding_id": str(task.get("finding_id") or ""),
            })
    return sorted(result, key=lambda item: (PRIORITIES[item["priority"]], item["index"]))


def team_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: dict[str, dict[str, int]] = {}
    for row in rows:
        team = row["team"]
        counts.setdefault(team, {"Tasks": 0, "Critical": 0, "High": 0})
        counts[team]["Tasks"] += 1
        if row["priority"] == "critical":
            counts[team]["Critical"] += 1
        if row["priority"] == "high":
            counts[team]["High"] += 1
    return [{"Team": name, **values}
            for name, values in sorted(counts.items(), key=lambda entry: (-entry[1]["Tasks"], entry[0]))]


def filter_team_tasks(rows: list[dict[str, Any]], *, team: str = "All", search: str = ""
                      ) -> list[dict[str, Any]]:
    needle = search.strip().casefold()
    return [row for row in rows
            if (team == "All" or row["team"] == team)
            and (not needle or needle in " ".join((row["title"], row["recommendation"],
                                                    row["team"], row["finding_id"])).casefold())]
