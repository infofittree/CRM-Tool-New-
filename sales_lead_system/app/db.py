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


# --------------------------------------------------------------------------- #
# Cached data loaders — avoid re-querying the remote DB on every Streamlit rerun.
# Short TTL keeps data fresh; write actions call clear_data_cache() for instant
# updates. Keyed by role + full_name so each salesperson's scope caches separately.
# --------------------------------------------------------------------------- #
@st.cache_data(ttl=45, show_spinner=False)
def load_leads_df(role: str, full_name: str, limit: int = 5000):
    """Cached scoped leads dataframe."""
    from modules.crm_service import CRMService
    with get_db().session_scope() as session:
        return CRMService(session).leads_dataframe({"role": role, "full_name": full_name}, limit)


@st.cache_data(ttl=45, show_spinner=False)
def load_tasks(role: str, full_name: str, upcoming_days: int = 7, max_today: int = 40):
    """Cached derived task queue."""
    from modules.crm_service import CRMService
    with get_db().session_scope() as session:
        return CRMService(session).get_tasks({"role": role, "full_name": full_name},
                                             upcoming_days=upcoming_days, max_today=max_today)


def clear_data_cache() -> None:
    """Invalidate cached reads after any write so the UI updates immediately."""
    load_leads_df.clear()
    load_tasks.clear()


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
