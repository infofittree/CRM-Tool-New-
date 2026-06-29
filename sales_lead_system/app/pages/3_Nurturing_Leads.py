"""Nurturing lead intelligence page — redesigned with health cards."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pandas as pd
import streamlit as st

from app.db import ensure_startup, get_db, render_startup_status
from app.ui import configure_page, data_table, empty_state, page_header, require_login, section_header
from modules.crm_service import CRMService


configure_page("Nurturing Leads")
user = require_login("Nurturing Leads")
page_header("Nurturing Leads", "Identify warm and cold nurturing accounts that need the next action.", "Pipeline Health")


def health(days: int | None) -> tuple[str, str]:
    if days is None:
        return "COLD", "call again"
    if days > 30:
        return "COLD", "reactivate or mark inactive"
    if days > 15:
        return "WARM", "send quotation reminder"
    if days > 7:
        return "WARM", "request feedback"
    return "HOT", "continue active nurturing"


db = get_db()
startup_status = ensure_startup(db)
render_startup_status(startup_status)
if startup_status.errors:
    st.error(startup_status.errors[0])
    st.stop()
with db.session_scope() as session:
    service = CRMService(session)
    leads = service.leads_dataframe(user)
    if not leads.empty and "standard_status" in leads.columns:
        nurturing = leads[leads["standard_status"] == "Nurturing"].copy()
    else:
        _nurture_values = {"Nurture", "NURTURING", "Nurturing", "nurture", "nurturing"}
        nurturing = leads[leads["status"].isin(_nurture_values)].copy() if not leads.empty else leads
    if nurturing.empty:
        empty_state("No nurturing leads right now", "When leads enter nurturing, their health and suggested actions will appear here.")
        st.stop()
    today = date.today()
    nurturing["days_since_last_contact"] = nurturing["last_contact_date"].apply(lambda d: (today - d).days if pd.notna(d) else None)
    nurturing[["health", "suggested_action"]] = nurturing["days_since_last_contact"].apply(lambda d: pd.Series(health(d)))

    section_header("Nurturing Queue", "Health is calculated from days since last contact.")
    data_table(
        nurturing[["lead_id", "company_name", "assigned_to", "days_since_last_contact", "lead_score", "health", "suggested_action", "remarks"]]
    )
