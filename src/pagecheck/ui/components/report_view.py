"""Apresentação de auditorias consolidadas, sem dependência da execução dos motores."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from pagecheck.ui.components.report_data import (
    SEVERITY_LABELS, STATUS_LABELS, export_report_json, issue_counts, module_rows,
    screenshot_entries,
)


def _score(value: object) -> str:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return f"{value:.0f}/100"
    return "Não verificado"


def render_report(report: dict[str, Any], *, root: Path) -> None:
    st.subheader("Resultado da auditoria")
    st.caption(f"{report['final_url']} · {report['niche']} · {report['objective']}")
    if report["status"] == "partial":
        st.warning("Auditoria parcial: fontes não executadas continuam como 'não verificadas'.")
    else:
        st.success("Fontes previstas para esta execução concluídas. Consulte a cobertura.")

    counts = issue_counts(report)
    seo = ((report.get("scores") or {}).get("internal") or {}).get("seo") or {}
    cols = st.columns(4)
    cols[0].metric("SEO Page Check", _score(seo.get("score")))
    cols[1].metric("Problemas", counts["failed"])
    cols[2].metric("Alertas", counts["warning"])
    cols[3].metric("Não verificados", counts["not_verified"])

    tab_summary, tab_journey, tab_issues, tab_visual, tab_teams, tab_data = st.tabs(
        ["Resumo", "URLs e parâmetros", "Problemas", "Capturas", "Equipes", "Dados"]
    )
    with tab_summary:
        st.caption("Notas do Lighthouse são independentes da nota de conformidade SEO do Page Check.")
        lh = (report.get("scores") or {}).get("lighthouse")
        if isinstance(lh, dict) and lh:
            st.markdown("**Lighthouse**")
            cols = st.columns(4)
            for col, (key, label) in zip(cols, (
                ("performance", "Performance"), ("accessibility", "Acessibilidade"),
                ("best-practices", "Boas práticas"), ("seo", "SEO Lighthouse"),
            )):
                col.metric(label, _score(lh.get(key)))
        st.markdown("**Resultados por área**")
        rows = module_rows(report)
        if rows:
            frame = pd.DataFrame(rows).set_index("Módulo")
            st.bar_chart(frame[["Problemas", "Atenção", "Aprovados"]], horizontal=True)
        else:
            st.info("Não há verificações por área disponíveis.")
        state = report.get("source_states") or {}
        with st.expander("Cobertura das fontes e limitações"):
            st.json(state, expanded=False)
            for limitation in report.get("limitations") or []:
                st.caption(str(limitation))
    with tab_journey:
        st.caption("Verificações observáveis no HTML e na URL. Não representam conversões registradas no Analytics.")
        related = [item for item in report.get("checks", [])
                   if item.get("module") in {"tracking", "navigation", "forms"}]
        if not related:
            st.info("Nenhum resultado de parâmetros, navegação ou formulários recebido.")
        else:
            for item in related:
                label = STATUS_LABELS.get(item.get("status"), "Não verificado")
                st.markdown(f"**{label} · {item.get('title', 'Verificação')}**")
                if item.get("recommendation"):
                    st.caption(item["recommendation"])
                with st.expander("Evidência técnica"):
                    st.json(item.get("evidence") or {}, expanded=False)
    with tab_issues:
        findings = report.get("findings") or []
        if not findings:
            st.info("Nenhum problema foi informado nos resultados recebidos. Isso não garante ausência de problemas.")
        else:
            st.caption(f"{len(findings)} achado(s), apresentados por prioridade automática")
            for item in findings:
                severity = SEVERITY_LABELS.get(item.get("severity"), "Atenção")
                heading = f"{severity} · {item.get('title', 'Verificação')}"
                with st.expander(heading):
                    st.write(f"**Área:** {item.get('module', '—')}  |  **Equipe:** {item.get('team', '—')}")
                    if item.get("description"):
                        st.write(item["description"])
                    if item.get("recommendation"):
                        st.write(f"**Ação:** {item['recommendation']}")
                    st.caption(f"Status: {STATUS_LABELS.get(item.get('status'), '—')} · Fonte: {item.get('source', '—')}")
                    if isinstance(item.get("evidence"), dict):
                        st.json(item["evidence"], expanded=False)
    with tab_visual:
        images = screenshot_entries(report, root)
        if not images:
            st.info("Este relatório não contém screenshots vinculados. A auditoria visual ainda não foi executada neste fluxo.")
        else:
            for viewport, path in images:
                st.markdown(f"**{viewport.capitalize()}**")
                st.image(str(path), caption=f"Captura de {viewport} com evidências", use_container_width=True)
        st.caption("Capturas só são exibidas quando fazem parte do relatório e estão na pasta local artifacts/.")
    with tab_teams:
        actions = report.get("actions_by_team") or []
        if not actions:
            st.info("Sem ações por equipe nos resultados recebidos.")
        for team in actions:
            if not isinstance(team, dict):
                continue
            with st.expander(f"{team.get('team', 'Equipe')} · {team.get('count', 0)} ações", expanded=True):
                for task in team.get("actions") or []:
                    if not isinstance(task, dict):
                        continue
                    st.write(f"**{task.get('title', 'Achado')}** · {SEVERITY_LABELS.get(task.get('priority'), task.get('priority', ''))}")
                    st.caption(task.get("action") or "Revisar o achado e sua evidência.")
    with tab_data:
        st.download_button(
            "Baixar relatório JSON", export_report_json(report),
            file_name="pagecheck_auditoria.json", mime="application/json",
        )
        st.caption("Exportação JSON disponível. Histórico SQLite e exportação visual ficam para a etapa seguinte.")
        with st.expander("JSON consolidado"):
            st.json(report, expanded=False)
