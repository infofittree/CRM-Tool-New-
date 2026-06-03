"""Settings and administration page."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
from sqlalchemy import select

from app.db import ensure_startup, get_db, render_startup_status
from app.ui import configure_page, page_header, require_login, section_header
from database.models import ALLOWED_STATUSES, AppSetting, PRIORITY_LEVELS, USER_ROLES, User
from modules.crm_service import CRMService, LEAD_SOURCES


configure_page("Settings")
user = require_login("Settings")
page_header("Settings", "Manage users, CRM options, and reminder rules.", "Administration")

db = get_db()
startup_status = ensure_startup(db)
render_startup_status(startup_status)
if startup_status.errors:
    st.error(startup_status.errors[0])
    st.stop()
with db.session_scope() as session:
    service = CRMService(session)
    tabs = st.tabs(["Users", "Statuses", "Lead Sources", "Reminder Rules"])

    with tabs[0]:
        section_header("Create User", "Add CRM users with role-based page access.")
        with st.form("create_user"):
            username = st.text_input("Username")
            full_name = st.text_input("Full Name")
            role = st.selectbox("Role", USER_ROLES)
            password = st.text_input("Temporary Password", type="password")
            submitted = st.form_submit_button("Create User")
        if submitted:
            service.create_user(username, password, full_name, role)
            st.success("User created.")
        users = session.scalars(select(User)).all()
        st.markdown("<div class='crm-table-shell'>", unsafe_allow_html=True)
        st.dataframe([{"username": u.username, "full_name": u.full_name, "role": u.role, "active": u.is_active} for u in users], use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with tabs[1]:
        section_header("Allowed Statuses", "Canonical lead stages used across imports and dashboard charts.")
        st.code(json.dumps(list(ALLOWED_STATUSES), indent=2))

    with tabs[2]:
        section_header("Lead Sources", "Available source labels for new and imported leads.")
        st.code(json.dumps(LEAD_SOURCES, indent=2))

    with tabs[3]:
        section_header("Reminder Rules", "Control inactivity thresholds used for lead health views.")
        medium_days = st.number_input("Medium priority: no contact after days", value=7, min_value=1)
        high_days = st.number_input("High priority: no contact after days", value=15, min_value=1)
        inactive_days = st.number_input("Inactive: no contact after days", value=30, min_value=1)
        if st.button("Save Reminder Thresholds"):
            value = json.dumps({"medium_days": medium_days, "high_days": high_days, "inactive_days": inactive_days})
            setting = session.get(AppSetting, "reminder_thresholds")
            if setting:
                setting.setting_value = value
            else:
                session.add(AppSetting(setting_key="reminder_thresholds", setting_value=value))
            st.success("Settings saved.")
