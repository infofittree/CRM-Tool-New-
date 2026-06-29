"""Sales team performance page — redesigned with leaderboard cards."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st

from app.db import ensure_startup, get_db, render_startup_status
from app.ui import configure_page, data_table, empty_state, page_header, require_login, section_header
from modules import dashboard_queries


configure_page("Sales Team")
user = require_login("Sales Team")
page_header("Sales Team Performance", "Compare assignments, active workload, conversions, and overdue follow-ups.", "Team Performance")

db = get_db()
startup_status = ensure_startup(db)
render_startup_status(startup_status)
if startup_status.errors:
    st.error(startup_status.errors[0])
    st.stop()
with db.session_scope() as session:
    leads = dashboard_queries.get_leads_dataframe(session, user, limit=5000)
    perf = dashboard_queries.get_salesperson_stats(session, user)

if leads.empty or perf.empty:
    empty_state("No team data available", "Assign leads to sales users to activate team performance reporting.")
    st.stop()

section_header("Leaderboard", "Top performers sorted by conversions and conversion rate.")
top = perf.sort_values(["conversions", "conversion_rate"], ascending=False).head(3)
data_table(top)

section_header("Team Details", "Operational workload across the team.")
data_table(perf.sort_values("assigned_leads", ascending=False))
