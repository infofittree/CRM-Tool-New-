"""Settings and administration page — redesigned with icon tabs."""

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
from app.ui import configure_page, data_table, page_header, require_login, section_header
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
        data_table([{"username": u.username, "full_name": u.full_name, "role": u.role, "active": u.is_active} for u in users])

        section_header("Delete User", "Admin only. Reassign or unassign their leads first.")
        if user["role"] != "Admin":
            st.info("Only Admins can delete users.")
        else:
            active_users = [u for u in users if u.is_active and u.username != user["username"]]
            if not active_users:
                st.caption("No other active users to delete.")
            else:
                del_username = st.selectbox("User to delete", [u.username for u in active_users])
                target = next(u for u in active_users if u.username == del_username)
                workload = service.user_workload(target.full_name or target.username)
                st.warning(f"**{del_username}** ({target.role}) currently owns **{workload['leads']} leads**.")
                mode = st.radio("What to do with their leads?",
                                ["Transfer to another user", "Unassign (clear owner)"], horizontal=True)
                transfer_to = None
                if mode.startswith("Transfer"):
                    others = [u.full_name or u.username for u in active_users if u.username != del_username]
                    transfer_to = st.selectbox("Transfer leads to", others) if others else None
                if not st.session_state.get(f"confirm_deluser_{del_username}"):
                    if st.button("Delete User", key=f"duser_{del_username}"):
                        st.session_state[f"confirm_deluser_{del_username}"] = True
                        st.rerun()
                else:
                    st.error(f"Confirm deletion of '{del_username}'? This is logged and reversible (account is deactivated).")
                    cc1, cc2 = st.columns(2)
                    if cc1.button("Yes, delete user", key=f"duyes_{del_username}"):
                        ok, msg = service.delete_user(del_username, user, transfer_to=transfer_to)
                        st.success(msg) if ok else st.error(msg)
                        st.session_state.pop(f"confirm_deluser_{del_username}", None)
                        st.rerun()
                    if cc2.button("Cancel", key=f"dunope_{del_username}"):
                        st.session_state.pop(f"confirm_deluser_{del_username}", None)
                        st.rerun()

    with tabs[1]:
        section_header("Status Configuration", "Current allowed statuses in the CRM.")
        for s in ALLOWED_STATUSES:
            st.markdown(f"- {s}")
        st.caption("Edit `config/validation_rules.json` to add or remove statuses.")

    with tabs[2]:
        section_header("Lead Sources", "Configured lead sources.")
        for s in LEAD_SOURCES:
            st.markdown(f"- {s}")
        st.caption("Edit `config/dropdown_options.json` to add or remove sources.")

    with tabs[3]:
        section_header("Reminder Rules", "Day-based rules for follow-up reminders.")
        try:
            rules = json.loads((Path(__file__).resolve().parents[2] / "config" / "reminder_rules.json").read_text())
        except Exception:
            rules = {"max_followup_days_ahead": 30, "overdue_after_days": 1}
        st.json(rules)
