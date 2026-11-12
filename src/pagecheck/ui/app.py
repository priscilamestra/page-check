"""Interface Streamlit do Page Check — Etapa 16.

O relatório completo só é exibido quando carregado ou fornecido pelas fontes.
Uma consulta ao endpoint SEO devolve um relatório PARCIAL: os demais motores
não são executados automaticamente por este formulário.
"""
from __future__ import annotations

import os
from pathlib import Path

import httpx
import streamlit as st

from pagecheck.ui.components.report_data import (
    OBJECTIVE_LABELS, local_demo_report, parse_uploaded_report, report_from_seo_response,
)
from pagecheck.ui.components.report_view import render_report

ROOT = Path(__file__).resolve().parents[3]


def _api_health(api_url: str) -> bool:
    try:
        response = httpx.get(f"{api_url}/health", timeout=2.0)
        response.raise_for_status()
        return response.json().get("status") == "ok"
    except (httpx.HTTPError, ValueError):
        return False


def _seo_live_report(api_url: str, *, url: str, niche: str, objective: str) -> dict:
    try:
        response = httpx.post(
            f"{api_url}/v1/audits/seo",
            json={"url": url, "niche": niche, "objective": objective},
            timeout=40.0,
        )
        response.raise_for_status()
        result = response.json()
    except httpx.HTTPStatusError as exc:
        message = str(exc.response.status_code)
        try:
            message = str(exc.response.json().get("detail") or message)
        except (ValueError, AttributeError):
            pass
        raise ValueError(f"A API não concluiu a auditoria SEO: {message}") from exc
    except (httpx.RequestError, ValueError) as exc:
        raise ValueError(f"Não foi possível consultar a API: {exc}") from exc
    return report_from_seo_response(result)


def render_app() -> None:
    st.set_page_config(page_title="Page Check", page_icon="🔎", layout="wide")
    st.title("Page Check")
    st.caption("Auditoria técnica e visual para páginas de aquisição e marketing · Sem IA generativa")

    api_url = os.getenv("PAGECHECK_API_URL", "http://127.0.0.1:8000").rstrip("/")
    with st.sidebar:
        st.markdown("### Fontes")
        if _api_health(api_url):
            st.success("FastAPI conectada")
        else:
            st.warning("FastAPI indisponível")
        st.caption("O backend SEO precisa estar ativo para uma consulta real.")
        st.markdown("### Estado do projeto")
        st.caption("Etapa 16: UI para dados consolidados e auditoria SEO real. Outros motores ainda não são executados pelo formulário.")

    st.subheader("Nova auditoria")
    with st.form("audit_form"):
        url = st.text_input("URL pública", placeholder="https://exemplo.com/landing-page")
        col_niche, col_goal = st.columns(2)
        with col_niche:
            niche = st.text_input("Nicho", placeholder="Tecnologia / SaaS")
        with col_goal:
            objective = st.selectbox(
                "Objetivo", list(OBJECTIVE_LABELS),
                format_func=lambda value: OBJECTIVE_LABELS[value],
            )
        run = st.form_submit_button("Auditar SEO da página", type="primary")
    st.caption("Esta consulta executa somente o SEO determinístico. Navegação, imagens, layout e motores externos permanecem não verificados neste fluxo.")
    if run:
        if not url.strip() or len(niche.strip()) < 2:
            st.error("Informe a URL e o nicho antes de executar.")
        else:
            with st.spinner("Consultando o endpoint SEO..."):
                try:
                    st.session_state["pagecheck_report"] = _seo_live_report(
                        api_url, url=url.strip(), niche=niche.strip(), objective=objective,
                    )
                    st.session_state["pagecheck_origin"] = "Auditoria SEO real (parcial)"
                except ValueError as exc:
                    st.error(str(exc))

    with st.expander("Abrir relatório existente ou dados de demonstração"):
        uploaded = st.file_uploader("Carregar relatório consolidado JSON", type=["json"])
        if st.button("Abrir JSON enviado", disabled=uploaded is None):
            try:
                if uploaded is None:
                    raise ValueError("Selecione um JSON.")
                st.session_state["pagecheck_report"] = parse_uploaded_report(uploaded.getvalue())
                st.session_state["pagecheck_origin"] = "JSON importado"
            except ValueError as exc:
                st.error(str(exc))
        if st.button("Carregar demonstração da Etapa 15"):
            try:
                st.session_state["pagecheck_report"] = local_demo_report(ROOT)
                st.session_state["pagecheck_origin"] = "Demonstração offline (dados de referência)"
            except (FileNotFoundError, ValueError) as exc:
                st.error(str(exc))

    report = st.session_state.get("pagecheck_report")
    if isinstance(report, dict):
        st.divider()
        st.caption(st.session_state.get("pagecheck_origin", "Relatório carregado"))
        render_report(report, root=ROOT)
    else:
        st.info("Execute uma auditoria SEO, carregue um JSON consolidado ou abra a demonstração para visualizar o painel.")
