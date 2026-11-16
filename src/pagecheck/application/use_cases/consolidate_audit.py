"""Monta um relatório único a partir de resultados JÁ coletados.

Não executa rede, Playwright, CLI, banco nem UI. Etapa 15: consolidação pura;
o orquestrador de execução completo será conectado nas próximas etapas.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pagecheck.reporting.consolidation.normalize import normalize_check
from pagecheck.reporting.consolidation.summary import (
    group_actions, priority_findings, summarize_checks,
)

ENGINE_NAMES = ("lighthouse", "axe", "impeccable")
VIEWPORT_NAMES = ("desktop", "mobile")


def _report(value: object, name: str) -> Mapping[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise TypeError(f"{name} deve ser um dicionário ou None.")
    return value


def _checks(value: Mapping[str, Any] | None, name: str) -> list[Mapping[str, Any]]:
    if value is None:
        return []
    records = value.get("checks")
    if not isinstance(records, list) or not all(isinstance(row, Mapping) for row in records):
        raise ValueError(f"{name}.checks precisa ser uma lista de objetos.")
    return records


def _findings(value: Mapping[str, Any] | None, name: str) -> list[Mapping[str, Any]]:
    if value is None:
        return []
    records = value.get("findings")
    if not isinstance(records, list) or not all(isinstance(row, Mapping) for row in records):
        raise ValueError(f"{name}.findings precisa ser uma lista de objetos.")
    return records


def consolidate_audit(
    *, requested_url: str, final_url: str, niche: str, objective: str,
    seo: Mapping[str, Any] | None = None,
    conversion: Mapping[str, Any] | None = None,
    visuals: Mapping[str, Mapping[str, Any]] | None = None,
    external: Mapping[str, Any] | None = None,
    audit_id: str | None = None,
    collected_at: str | None = None,
) -> dict[str, Any]:
    """Converte resultados de fontes diferentes em DTO JSON serializável.

    - SEO é o único score interno preservado nesta fase.
    - Lighthouse mantém suas notas originais e independentes.
    - A falta de um motor resulta em `not_verified`, nunca em nota zero.
    - Achados de Playwright são apenas falhas/alertas: sua ausência não prova
      que a página passou em todas as verificações visuais.
    """
    if not all(isinstance(x, str) and x.strip() for x in
               (requested_url, final_url, niche, objective)):
        raise ValueError("URL, URL final, nicho e objetivo são obrigatórios.")
    seo = _report(seo, "seo")
    conversion = _report(conversion, "conversion")
    external = _report(external, "external")
    if visuals is None:
        visuals = {}
    if not isinstance(visuals, Mapping):
        raise TypeError("visuals deve ser um mapeamento por viewport.")
    unexpected_viewports = set(visuals) - set(VIEWPORT_NAMES)
    if unexpected_viewports:
        raise ValueError(f"Viewports não reconhecidas: {sorted(unexpected_viewports)!r}")

    checks: list[dict[str, Any]] = []
    source_states: dict[str, Any] = {"seo": "not_verified", "conversion": "not_verified",
                                     "visuals": {}, "engines": {}}
    if seo is not None:
        for row in _checks(seo, "seo"):
            checks.append(normalize_check(row, source="seo_rules", page_url=final_url,
                                          default_module="seo"))
        source_states["seo"] = "completed"
    if conversion is not None:
        for row in _checks(conversion, "conversion"):
            checks.append(normalize_check(row, source="html_rules", page_url=final_url,
                                          default_module="conversion"))
        source_states["conversion"] = "completed"

    screenshot_refs: dict[str, Any] = {}
    design_reviews: dict[str, Any] = {}
    visual_limitations: dict[str, list[str]] = {}
    for viewport in VIEWPORT_NAMES:
        observation = _report(visuals.get(viewport), f"visuals.{viewport}")
        if observation is None:
            source_states["visuals"][viewport] = "not_verified"
            continue
        for row in _findings(observation, f"visuals.{viewport}"):
            checks.append(normalize_check(row, source="playwright", page_url=final_url,
                                          default_module="visual", viewport=viewport))
        warnings = []
        if isinstance(observation.get("limitations"), list):
            warnings.extend(str(v) for v in observation["limitations"])
        if observation.get("scroll_complete") is False:
            warnings.append("Scroll não concluído: parte da página pode não ter sido inspecionada.")
        geometry = observation.get("geometry")
        if isinstance(geometry, Mapping) and geometry.get("truncated") is True:
            warnings.append("Captura limitada/truncada pela política de recursos.")
        images = observation.get("images")
        if isinstance(images, Mapping) and (images.get("not_verified") or 0) > 0:
            warnings.append("Parte das imagens não pôde ser verificada.")
        visual_limitations[viewport] = warnings
        source_states["visuals"][viewport] = "partial" if warnings else "completed"
        if isinstance(observation.get("screenshots"), Mapping):
            screenshot_refs[viewport] = dict(observation["screenshots"])
        if isinstance(observation.get("design_review"), Mapping):
            design_reviews[viewport] = dict(observation["design_review"])

    engine_data = external.get("engines", external) if external is not None else {}
    if not isinstance(engine_data, Mapping):
        raise ValueError("external.engines deve ser um objeto.")
    lighthouse_scores: dict[str, Any] | None = None
    engine_limitations: dict[str, list[str]] = {}
    for engine in ENGINE_NAMES:
        item = _report(engine_data.get(engine), f"external.{engine}")
        valid = bool(item is not None and item.get("engine") == engine and
                     item.get("status") == "completed")
        source_states["engines"][engine] = "completed" if valid else "not_verified"
        if not valid:
            engine_limitations[engine] = (
                [str(x) for x in item.get("limitations", [])]
                if item is not None and isinstance(item.get("limitations"), list)
                else ["Motor indisponível, não executado ou saída não confirmada."])
            continue
        for row in _findings(item, f"external.{engine}"):
            checks.append(normalize_check(row, source=engine, page_url=final_url,
                                          default_module=engine))
        engine_limitations[engine] = (
            [str(x) for x in item.get("limitations", [])]
            if isinstance(item.get("limitations"), list) else [])
        if engine == "lighthouse" and isinstance(item.get("scores"), Mapping):
            lighthouse_scores = dict(item["scores"])

    # IDs estáveis são preservados. IDs duplicados ganham sufixo determinístico,
    # sem descartar evidências de fontes ou viewports diferentes.
    collisions: dict[str, int] = {}
    for item in checks:
        original = item["id"]
        collisions[original] = collisions.get(original, 0) + 1
        if collisions[original] > 1:
            item["id"] = f"{original}#{collisions[original]}"

    priority = priority_findings(checks)
    summary = summarize_checks(checks)
    by_module: dict[str, dict[str, int]] = {}
    for row in checks:
        module = row["module"]
        if module not in by_module:
            by_module[module] = {name: 0 for name in
                                 ("passed", "failed", "warning", "not_verified", "not_applicable")}
        by_module[module][row["status"]] += 1

    statuses = [source_states["seo"], source_states["conversion"],
                *source_states["visuals"].values(), *source_states["engines"].values()]
    # `partial` aponta cobertura incompleta; não significa fracasso do processo.
    data_status = ("completed" if all(s == "completed" for s in statuses) and
                   summary["counts"]["not_verified"] == 0 else "partial")
    internal_seo = None
    if seo is not None:
        internal_seo = {
            "score": seo.get("score"),
            "coverage": seo.get("coverage"),
            "partial_score": seo.get("partial_score"),
            "ruleset_version": seo.get("ruleset_version"),
        }

    return {
        "schema_version": "audit-report-1.0",
        "audit_id": audit_id,
        "collected_at": collected_at,
        "requested_url": requested_url,
        "final_url": final_url,
        "niche": niche,
        "objective": objective,
        "status": data_status,
        "source_states": source_states,
        "summary": {**summary, "by_module": dict(sorted(by_module.items())),
                    "priority_count": len(priority)},
        "scores": {"overall": None, "internal": {"seo": internal_seo},
                   "lighthouse": lighthouse_scores},
        "findings": priority,
        "checks": checks,
        "actions_by_team": group_actions(priority),
        "screenshots": screenshot_refs,
        "design_reviews": design_reviews,
        "engine_limitations": engine_limitations,
        "visual_limitations": visual_limitations,
        "limitations": [
            "Sem score geral: as notas do Lighthouse não se somam às notas Page Check.",
            "Cobertura de checks reflete apenas regras recebidas e não comprova auditoria integral.",
            "Módulos não executados permanecem not_verified; ausência de achados não prova sucesso.",
        ],
    }
