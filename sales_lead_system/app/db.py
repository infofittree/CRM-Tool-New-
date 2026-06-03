"""Streamlit database resource helpers."""

from __future__ import annotations

import streamlit as st

from config.settings import LOG_DIR
from database.db_connection import DatabaseConnection
from app.startup import StartupStatus, initialize_crm
from modules.logger import setup_logger


@st.cache_resource(show_spinner=False)
def get_db() -> DatabaseConnection:
    """Return cached pooled database connection."""
    return DatabaseConnection(logger=setup_logger(LOG_DIR))


def ensure_startup(db: DatabaseConnection, force_sync: bool = False) -> StartupStatus:
    """Run CRM startup once per Streamlit session and return the latest status."""
    if force_sync or "startup_status" not in st.session_state:
        messages: list[tuple[str, str]] = []

        def progress(label: str, detail: str) -> None:
            messages.append((label, detail))

        with st.spinner("Preparing CRM data connection..."):
            status = initialize_crm(db, progress=progress, force_sync=force_sync)
        st.session_state["startup_status"] = status
        st.session_state["startup_progress"] = messages
    return st.session_state["startup_status"]


def render_startup_status(status: StartupStatus) -> None:
    """Show compact startup validation state in the sidebar."""
    with st.sidebar:
        st.caption("System Status")
        _status_line("MySQL Connected", status.mysql_connected)
        _status_line("Tables Loaded", status.tables_loaded)
        _status_line("Excel Synced", status.excel_synced)
        _status_line("Dashboard Ready", status.dashboard_ready)
        if st.button("Refresh Data", use_container_width=True):
            ensure_startup(get_db(), force_sync=True)
            st.cache_data.clear()
            st.rerun()


def _status_line(label: str, ok: bool) -> None:
    css = "crm-status-ok" if ok else "crm-status-bad"
    text = "OK" if ok else "Needs attention"
    st.markdown(
        f"<div class='crm-status-line'><span>{label}</span><span class='{css}'>{text}</span></div>",
        unsafe_allow_html=True,
    )
