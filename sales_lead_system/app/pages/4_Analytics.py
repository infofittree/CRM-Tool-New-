"""Interactive analytics dashboard."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pandas as pd
import plotly.express as px
import streamlit as st

from app.assets.theme import STATUS_COLORS, style_plotly
from app.db import ensure_startup, get_db, render_startup_status
from app.ui import configure_page, empty_state, page_header, require_login, section_header
from modules.crm_service import CRMService


configure_page("Analytics")
user = require_login("Analytics")
page_header("Analytics", "Explore lead sources, status distribution, geography, and follow-up trends.", "CRM Intelligence")

db = get_db()
startup_status = ensure_startup(db)
render_startup_status(startup_status)
if startup_status.errors:
    st.error(startup_status.errors[0])
    st.stop()
with db.session_scope() as session:
    service = CRMService(session)
    leads = service.leads_dataframe(user, limit=5000)
    followups = service.followups_dataframe(user, horizon_days=365)

if leads.empty:
    empty_state("No analytics data available", "Import or create leads to generate charts.")
    st.stop()

source_filter = st.multiselect("Lead Source", sorted(leads["lead_source"].dropna().unique()))
status_filter = st.multiselect("Status", sorted(leads["status"].dropna().unique()))
filtered = leads.copy()
if source_filter:
    filtered = filtered[filtered["lead_source"].isin(source_filter)]
if status_filter:
    filtered = filtered[filtered["status"].isin(status_filter)]

col1, col2 = st.columns(2)
with col1:
    section_header("Lead Sources", "Where the current pipeline is coming from.")
    st.plotly_chart(style_plotly(px.histogram(filtered, x="lead_source", title="Lead Source Analysis")), use_container_width=True)
    section_header("Salesperson Mix", "Lead status by assignee.")
    st.plotly_chart(
        style_plotly(px.histogram(filtered, x="assigned_to", color="status", title="Salesperson Performance", color_discrete_map=STATUS_COLORS)),
        use_container_width=True,
    )
with col2:
    section_header("Status Distribution", "Current breakdown of lead stages.")
    st.plotly_chart(style_plotly(px.pie(filtered, names="status", title="Lead Status Distribution", color="status", color_discrete_map=STATUS_COLORS)), use_container_width=True)
    section_header("Country Analysis", "Lead concentration by geography.")
    st.plotly_chart(style_plotly(px.histogram(filtered, x="country", title="Country-wise Lead Analysis")), use_container_width=True)

if not followups.empty:
    followups["month"] = pd.to_datetime(followups["next_followup"], errors="coerce").dt.to_period("M").astype(str)
    section_header("Monthly Follow-up Trend", "Upcoming and overdue touchpoints by month.")
    st.plotly_chart(style_plotly(px.histogram(followups, x="month", title="Follow-up Completion / Schedule Trend")), use_container_width=True)
