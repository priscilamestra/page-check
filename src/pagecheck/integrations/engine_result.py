"""Contrato comum para resultados de ferramentas externas, sem dependências de UI."""
from __future__ import annotations

from typing import Any


class EngineOutputError(ValueError):
    """Um motor respondeu com formato que não pode ser interpretado."""


def result(engine: str, *, scores: dict[str, int | None] | None = None,
           findings: list[dict[str, Any]] | None = None,
           metrics: dict[str, Any] | None = None,
           limitations: list[str] | None = None) -> dict[str, Any]:
    return {
        "engine": engine,
        "status": "completed",
        "scores": scores or {},
        "metrics": metrics or {},
        "findings": findings or [],
        "limitations": limitations or [],
    }


def unavailable(engine: str, reason: str) -> dict[str, Any]:
    return {
        "engine": engine, "status": "not_verified", "scores": {},
        "metrics": {}, "findings": [], "limitations": [reason],
    }


def require_mapping(value: object, name: str) -> dict:
    if not isinstance(value, dict):
        raise EngineOutputError(f"{name} deve ser um objeto JSON.")
    return value
