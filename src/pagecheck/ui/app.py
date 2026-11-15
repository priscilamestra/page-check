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
from pagecheck.ui.history_labels import history_option_label
from pagecheck.ui.history_resume import (
    clear_active_audit, remember_active_audit, resume_active_audit,
)

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
            timeout=120.0,
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


def _save_history(api_url: str, report: dict) -> str:
    try:
        response = httpx.post(f"{api_url}/v1/history", json=report, timeout=15.0)
        response.raise_for_status()
        return str(response.json()["audit_id"])
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        raise ValueError("The audit ran, but it could not be saved in local history.") from exc


def _history_items(api_url: str) -> list[dict]:
    response = httpx.get(f"{api_url}/v1/history", params={"limit": 30}, timeout=5.0)
    response.raise_for_status()
    return response.json()["items"]


def _load_history(api_url: str, audit_id: str) -> dict:
    response = httpx.get(f"{api_url}/v1/history/{audit_id}", timeout=10.0)
    response.raise_for_status()
    return validate_report(response.json())


def _delete_history(api_url: str, audit_id: str) -> None:
    response = httpx.delete(f"{api_url}/v1/history/{audit_id}", timeout=10.0)
    response.raise_for_status()


def render_app() -> None:
    st.set_page_config(page_title="Page Check", page_icon="🔎", layout="wide",
                       initial_sidebar_state="collapsed")

    api_url = os.getenv("PAGECHECK_API_URL", "http://127.0.0.1:8000").rstrip("/")
    try:
        resume_active_audit(
            st.session_state, st.query_params,
            lambda audit_id: _load_history(api_url, audit_id),
        )
    except (httpx.HTTPError, ValueError, KeyError):
        clear_active_audit(st.session_state, st.query_params)
        st.warning(
            "The last opened saved audit is no longer available. "
            "Choose another report from history."
        )
    # Native top-of-page popover: no sidebar and no fragile toolbar CSS hacks.
    # The native Streamlit "Deploy" button belongs to Streamlit's browser chrome;
    # the connection/tools menu sits at the right edge of app content below it.
    is_production = os.getenv("PAGECHECK_ENV", "local").strip().lower() == "production"
    heading, tools = st.columns([9, 1.6], vertical_alignment="top")
    with heading:
        st.title("Page Check")
        st.caption("Technical, SEO, and conversion-readiness audits · No generative AI")
    with tools:
        with st.popover("Connection" if is_production else "Tools",
                        icon=":material/tune:", use_container_width=False):
            st.markdown("**Connection**")
            if _api_health(api_url):
                st.badge("FastAPI connected", color="green")
            else:
                st.badge("FastAPI offline", color="gray")
            st.caption("Live audits require the API server.")
            if not is_production:
                with st.expander("Developer tools"):
                    st.caption("HTML audit: SEO, URL parameters, links, CTAs, and forms. "
                               "Browser capture is optional and requires local opt-in; "
                               "static external engines require PAGECHECK_ALLOW_LOCAL_STATIC_ENGINES=1; "
                               "Lighthouse is limited to trusted local fixtures.")
                    if st.button("Load sample report"):
                        try:
                            clear_active_audit(st.session_state, st.query_params)
                            st.session_state["pagecheck_report"] = local_demo_report(ROOT)
                            st.session_state["pagecheck_origin"] = "Sample data · not a live audit"
                            st.session_state.pop("pagecheck_history_notice", None)
                            st.rerun()
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
        "alignment, URL parameters, links, CTAs, and HTML forms. "
        "Desktop/mobile screenshots are added only when the local FastAPI "
        "has PAGECHECK_ALLOW_LIVE_BROWSER=1. JavaScript remains disabled. "
        "Static external engine checks require an explicit local opt-in; "
        "Lighthouse is not run against arbitrary public URLs."
    )
    if run:
        if not url.strip() or len(niche.strip()) < 2:
            st.error("Enter a valid public URL and an industry or niche.")
        elif not keywords:
            st.error("Add at least one target keyword to guide the content audit.")
        else:
            with st.spinner("Auditing HTML and capturing available visual evidence..."):
                try:
                    clear_active_audit(st.session_state, st.query_params)
                    st.session_state["pagecheck_report"] = _page_live_report(
                        api_url, url=url.strip(), niche=niche.strip(),
                        objective=objective, language=language, keywords=keywords,
                    )
                    visual_states = st.session_state["pagecheck_report"].get("source_states", {}).get("visuals", {})
                    visual_done = any(value in {"completed", "partial"} for value in visual_states.values())
                    st.session_state["pagecheck_origin"] = (
                        "Live HTML audit · visual evidence captured (limited)" if visual_done
                        else "Live HTML audit · visual checks not verified"
                    )
                    try:
                        saved_id = _save_history(api_url, st.session_state["pagecheck_report"])
                        remember_active_audit(st.session_state, st.query_params, saved_id)
                        st.session_state["pagecheck_history_notice"] = (
                            f"Audit saved to local history ({saved_id[:8]})."
                        )
                    except ValueError as exc:
                        st.session_state["pagecheck_history_notice"] = str(exc)
                except ValueError as exc:
                    st.error(str(exc))

    with st.expander("Import an existing audit report"):
        uploaded = st.file_uploader("Consolidated JSON report", type=["json"])
        if st.button("Open imported report", disabled=uploaded is None):
            try:
                if uploaded is None:
                    raise ValueError("Choose a JSON report first.")
                clear_active_audit(st.session_state, st.query_params)
                st.session_state["pagecheck_report"] = parse_uploaded_report(uploaded.getvalue())
                st.session_state["pagecheck_origin"] = "Imported report"
                st.session_state.pop("pagecheck_history_notice", None)
            except ValueError as exc:
                st.error(str(exc))

    with st.expander("Saved audits · local history"):
        st.caption("Saved on this computer. Opening a report does not run the audit again.")
        try:
            history = _history_items(api_url)
        except (httpx.HTTPError, ValueError, KeyError):
            history = []
            st.caption("History is unavailable. Check that the local FastAPI server is running.")
        if not history:
            st.caption("No saved audits yet.")
        else:
            choices = {item["id"]: item for item in history}
            # The browser timezone is the user's location, not the server's.
            # ISO/UTC is retained inside SQLite for accurate sorting and storage.
            client_timezone = getattr(st.context, "timezone", None)
            client_offset = getattr(st.context, "timezone_offset", None)
            choice = st.selectbox(
                "Choose a saved audit", options=list(choices),
                format_func=lambda audit_id: history_option_label(
                    choices[audit_id], browser_timezone=client_timezone,
                    browser_offset_minutes=client_offset,
                ),
                key="pagecheck_selected_history",
                index=(list(choices).index(st.query_params.get("audit"))
                       if st.query_params.get("audit") in choices else 0),
            )
            if st.button("Open saved audit"):
                try:
                    report = _load_history(api_url, choice)
                    st.session_state["pagecheck_report"] = report
                    remember_active_audit(st.session_state, st.query_params, choice)
                    st.session_state["pagecheck_origin"] = "Saved audit · local history"
                    st.session_state.pop("pagecheck_history_notice", None)
                    st.rerun()
                except (httpx.HTTPError, ValueError, KeyError) as exc:
                    st.error(f"Could not open saved audit: {exc}")
            with st.expander("Delete saved audit"):
                st.caption("This permanently deletes the selected saved report and its copied screenshots.")
                confirm = st.checkbox("I understand this cannot be undone", key=f"pagecheck_history_delete_{choice}")
                if st.button("Delete selected audit", disabled=not confirm):
                    try:
                        _delete_history(api_url, choice)
                        if st.session_state.get("pagecheck_active_history_id") == choice:
                            clear_active_audit(st.session_state, st.query_params)
                            st.session_state.pop("pagecheck_report", None)
                            st.session_state.pop("pagecheck_origin", None)
                        st.session_state.pop("pagecheck_history_notice", None)
                        st.rerun()
                    except httpx.HTTPError as exc:
                        st.error(f"Could not delete saved audit: {exc}")

    if st.session_state.get("pagecheck_history_notice"):
        st.caption(st.session_state["pagecheck_history_notice"])

    report = st.session_state.get("pagecheck_report")
    if isinstance(report, dict):
        st.divider()
        st.caption(st.session_state.get("pagecheck_origin", "Loaded audit report"))
        render_report(report, root=ROOT)
    else:
        st.info("Enter a public URL, choose the content language, and add target keywords to begin.")
