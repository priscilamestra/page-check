"""English-language Page Check UI with multilingual content-audit inputs."""
from __future__ import annotations

import os
from pathlib import Path

import httpx
import streamlit as st

from pagecheck.ui.components.report_data import (
    OBJECTIVE_LABELS, local_demo_report, parse_uploaded_report, validate_report,
)
from pagecheck.ui.components.report_view import render_report

ROOT = Path(__file__).resolve().parents[3]
CONTENT_LANGUAGES = {"en": "English", "pt": "Portuguese", "es": "Spanish"}


def _api_health(api_url: str) -> bool:
    try:
        response = httpx.get(f"{api_url}/health", timeout=2.0)
        response.raise_for_status()
        return response.json().get("status") == "ok"
    except (httpx.HTTPError, ValueError):
        return False


def _page_live_report(api_url: str, *, url: str, niche: str, objective: str,
                      language: str = "en", keywords: list[str] | None = None) -> dict:
    try:
        response = httpx.post(
            f"{api_url}/v1/audits/page",
            json={"url": url, "niche": niche, "objective": objective,
                  "language": language, "keywords": keywords or []},
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
        if exc.response.status_code == 503:
            raise ValueError(
                "Live URL fetching is disabled in the API. For local development, "
                "restart FastAPI with PAGECHECK_ALLOW_LIVE_FETCH=1."
            ) from exc
        raise ValueError(f"The audit could not be completed: {message}") from exc
    except httpx.RequestError as exc:
        raise ValueError(f"Could not reach the API: {exc}") from exc
    return validate_report(result)


def render_app() -> None:
    st.set_page_config(page_title="Page Check", page_icon="🔎", layout="wide")
    st.title("Page Check")
    st.caption("Technical, SEO, and conversion-readiness audits · No generative AI")

    api_url = os.getenv("PAGECHECK_API_URL", "http://127.0.0.1:8000").rstrip("/")
    with st.sidebar:
        st.markdown("### Connection")
        if _api_health(api_url):
            st.success("FastAPI connected")
        else:
            st.warning("FastAPI unavailable")
        st.caption("Live audits require the local API server.")
        with st.expander("Developer tools"):
            st.caption("HTML audit: SEO, URL parameters, links, CTAs, and forms. "
                       "Browser screenshots and external engines are not run here yet.")
            if st.button("Load sample report"):
                try:
                    st.session_state["pagecheck_report"] = local_demo_report(ROOT)
                    st.session_state["pagecheck_origin"] = "Sample data · not a live audit"
                except (FileNotFoundError, ValueError) as exc:
                    st.error(str(exc))

    st.subheader("New audit")
    with st.form("audit_form"):
        url = st.text_input("Public page URL", placeholder="https://your-domain.com/page")
        left, middle, right = st.columns([2, 1, 2])
        with left:
            niche = st.text_input(
                "Industry or niche", placeholder="Enter the industry or market",
                help="Describe the market in the language you selected. No preset niches are required.",
            )
        with middle:
            language = st.selectbox(
                "Content language", options=list(CONTENT_LANGUAGES),
                format_func=lambda code: CONTENT_LANGUAGES[code],
                help="Language to compare against the page HTML and its target keywords. "
                     "The Page Check interface stays in English.",
            )
        with right:
            objective = st.selectbox(
                "Page goal", list(OBJECTIVE_LABELS),
                format_func=lambda value: OBJECTIVE_LABELS[value],
            )
        keywords = st.multiselect(
            "Target keywords", options=[], accept_new_options=True,
            max_selections=8, placeholder="Type a keyword and press Enter",
            help="Add up to eight words or phrases. These guide content checks; "
                 "they do not replace technical SEO checks or query Google rankings.",
        )
        run = st.form_submit_button("Audit page", type="primary")
    st.caption(
        "Checks available in this flow: technical SEO, selected-language and keyword "
        "alignment, URL parameters, links, CTAs, and HTML forms. Browser and screenshot "
        "checks will be connected separately."
    )
    if run:
        if not url.strip() or len(niche.strip()) < 2:
            st.error("Enter a valid public URL and an industry or niche.")
        elif not keywords:
            st.error("Add at least one target keyword to guide the content audit.")
        else:
            with st.spinner("Checking page HTML, SEO, keywords, and URL parameters..."):
                try:
                    st.session_state["pagecheck_report"] = _page_live_report(
                        api_url, url=url.strip(), niche=niche.strip(),
                        objective=objective, language=language, keywords=keywords,
                    )
                    st.session_state["pagecheck_origin"] = "Live HTML audit · visual checks pending"
                except ValueError as exc:
                    st.error(str(exc))

    with st.expander("Import an existing audit report"):
        uploaded = st.file_uploader("Consolidated JSON report", type=["json"])
        if st.button("Open imported report", disabled=uploaded is None):
            try:
                if uploaded is None:
                    raise ValueError("Choose a JSON report first.")
                st.session_state["pagecheck_report"] = parse_uploaded_report(uploaded.getvalue())
                st.session_state["pagecheck_origin"] = "Imported report"
            except ValueError as exc:
                st.error(str(exc))

    report = st.session_state.get("pagecheck_report")
    if isinstance(report, dict):
        st.divider()
        st.caption(st.session_state.get("pagecheck_origin", "Loaded audit report"))
        render_report(report, root=ROOT)
    else:
        st.info("Enter a public URL, choose the content language, and add target keywords to begin.")
