"""Streamlit login workflow."""

from __future__ import annotations

import os
from base64 import b64encode

import streamlit as st
from sqlalchemy import select

from app.ui import LOGO_PATH
from app.security import hash_password, verify_password
from database.db_connection import DatabaseConnection
from database.models import Base, User
from database.schema_manager import ensure_phase2_schema


def ensure_default_admin(db: DatabaseConnection) -> None:
    """Create a first admin user when the users table is empty."""
    Base.metadata.create_all(db.engine)
    ensure_phase2_schema(db.engine)
    username = os.getenv("CRM_ADMIN_USER", "admin")
    password = os.getenv("CRM_ADMIN_PASSWORD", "admin123")
    with db.session_scope() as session:
        has_user = session.scalar(select(User.user_id).limit(1))
        if has_user:
            return
        session.add(
            User(
                username=username,
                password_hash=hash_password(password),
                full_name="System Admin",
                role="Admin",
                is_active=True,
            )
        )


def render_login(db: DatabaseConnection) -> bool:
    """Render login form and update session state."""
    ensure_default_admin(db)
    logo_html = ""
    if LOGO_PATH.exists():
        logo_data = b64encode(LOGO_PATH.read_bytes()).decode("ascii")
        logo_html = f"<img class='crm-login-logo' src='data:image/png;base64,{logo_data}' />"

    # NOTE: do NOT wrap the form in a raw full-height <div> — Streamlit renders it
    # as a separate empty block, creating a 100vh white box that hides the form.
    left, center, right = st.columns([1, 1.4, 1])
    with center:
        st.markdown(
            f"""
            <div class="crm-login-card">
                {logo_html}
                <div class="crm-login-title">FitTree CRM</div>
                <div class="crm-login-subtitle">Sign in to manage leads, follow-ups, and sales activity.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login", use_container_width=True)
    if not submitted:
        return False

    with db.session_scope() as session:
        user = session.scalar(select(User).where(User.username == username, User.is_active.is_(True), User.deleted_at.is_(None)))
        if user and verify_password(password, user.password_hash):
            st.session_state["authenticated"] = True
            st.session_state["user"] = {
                "username": user.username,
                "full_name": user.full_name,
                "role": user.role,
            }
            st.success("Login successful.")
            st.rerun()
            return True
    st.error("Invalid username or password.")
    return False
