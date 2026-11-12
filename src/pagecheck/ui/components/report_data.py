"""Preparação segura e pura de dados para o dashboard Streamlit.

Não faz acesso à rede, não executa auditorias e não altera os resultados.
"""
from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pagecheck.application.use_cases.consolidate_audit import consolidate_audit

REPORT_SCHEMA = "audit-report-1.0"
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_SCREENSHOT_BYTES = 20 * 1024 * 1024
STATUS_LABELS = {
    "passed": "Passed", "failed": "Issue", "warning": "Needs review",
    "not_verified": "Not verified", "not_applicable": "Not applicable",
}
SEVERITY_LABELS = {
    "critical": "Critical", "high": "High", "medium": "Medium",
    "low": "Low", "info": "Info",
}
OBJECTIVE_LABELS = {
    "leads": "Generate leads", "meetings": "Book meetings",
    "sales": "Drive sales", "signup": "Get sign-ups",
    "organic_traffic": "Organic traffic",
}


def validate_report(payload: object) -> dict[str, Any]:
    """Valida contrato mínimo para não tratar um JSON arbitrário como auditoria."""
    if not isinstance(payload, dict) or payload.get("schema_version") != REPORT_SCHEMA:
        raise ValueError("O arquivo não usa o formato audit-report-1.0 do Page Check.")
    for key in ("requested_url", "final_url", "niche", "objective", "status"):
        if not isinstance(payload.get(key), str) or not payload[key].strip():
            raise ValueError(f"Campo obrigatório ausente ou inválido: {key}")
    if payload["status"] not in {"completed", "partial"}:
        raise ValueError("Status de relatório inválido.")
    if not isinstance(payload.get("scores"), dict):
        raise ValueError("Pontuações ausentes ou inválidas.")
    if not isinstance(payload.get("summary"), dict):
        raise ValueError("Resumo ausente ou inválido.")
    for key in ("checks", "findings", "actions_by_team"):
        if not isinstance(payload.get(key), list):
            raise ValueError(f"Coleção obrigatória inválida: {key}")
        if any(not isinstance(item, dict) for item in payload[key]):
            raise ValueError(f"Registros inválidos em {key}")
    if not isinstance(payload.get("source_states"), dict):
        raise ValueError("Estados das fontes ausentes.")
    return payload


def parse_uploaded_report(raw: bytes) -> dict[str, Any]:
    if len(raw) > MAX_UPLOAD_BYTES:
        raise ValueError("O relatório excede o limite de 5 MB.")
    try:
        parsed = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("O arquivo não é um JSON UTF-8 válido.") from exc
    return validate_report(parsed)


def report_from_seo_response(result: Mapping[str, Any]) -> dict[str, Any]:
    """Uma auditoria SEO real resulta em relatório parcial, nunca auditoria completa."""
    for key in ("requested_url", "final_url", "niche", "objective"):
        if not isinstance(result.get(key), str) or not result[key].strip():
            raise ValueError(f"Resposta SEO sem campo válido: {key}")
    report = consolidate_audit(
        requested_url=result["requested_url"],
        final_url=result["final_url"],
        niche=result["niche"],
        objective=result["objective"],
        seo=result,
    )
    return validate_report(report)


def local_demo_report(root: Path) -> dict[str, Any]:
    file = root / "artifacts" / "consolidation_stage15" / "consolidated_audit.json"
    if not file.is_file():
        raise FileNotFoundError(
            "Gere primeiro o exemplo: uv run python scripts/consolidation_fixture_smoke.py"
        )
    return parse_uploaded_report(file.read_bytes())


def safe_screenshot_path(value: object, root: Path) -> Path | None:
    """Permite renderizar apenas PNGs locais dentro de artifacts/, nunca caminhos externos."""
    if not isinstance(value, (str, Path)) or not str(value).strip():
        return None
    allowed_root = (root / "artifacts").resolve()
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = root / candidate
    candidate = candidate.resolve()
    if not candidate.is_relative_to(allowed_root) or candidate.suffix.lower() != ".png":
        return None
    try:
        if not candidate.is_file() or candidate.stat().st_size > MAX_SCREENSHOT_BYTES:
            return None
    except OSError:
        return None
    return candidate


def screenshot_entries(report: Mapping[str, Any], root: Path) -> list[tuple[str, Path]]:
    raw = report.get("screenshots", {})
    if not isinstance(raw, Mapping):
        return []
    images: list[tuple[str, Path]] = []
    for viewport in ("desktop", "mobile"):
        values = raw.get(viewport)
        if not isinstance(values, Mapping):
            continue
        path = safe_screenshot_path(values.get("annotated") or values.get("after_scroll"), root)
        if path:
            images.append((viewport, path))
    return images


def issue_counts(report: Mapping[str, Any]) -> dict[str, int]:
    raw = report.get("summary", {}).get("counts", {})
    if not isinstance(raw, Mapping):
        raw = {}
    return {status: int(raw.get(status) or 0) for status in STATUS_LABELS}


def module_rows(report: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw = report.get("summary", {}).get("by_module", {})
    if not isinstance(raw, Mapping):
        return []
    output = []
    for module, counts in sorted(raw.items()):
        if isinstance(counts, Mapping):
            output.append({"Módulo": module, "Problemas": int(counts.get("failed") or 0),
                           "Atenção": int(counts.get("warning") or 0),
                           "Aprovados": int(counts.get("passed") or 0)})
    return output


def export_report_json(report: Mapping[str, Any]) -> str:
    return json.dumps(report, ensure_ascii=False, indent=2)
