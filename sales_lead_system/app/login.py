"""Streamlit login workflow — glassmorphism redesign."""

from __future__ import annotations

import os
from base64 import b64encode

import streamlit as st
from sqlalchemy import select

from app.ui import LOGO_PATH
from app.security import verify_password
from app.startup import ensure_default_admin
from database.db_connection import DatabaseConnection
from database.models import User


def render_login(db: DatabaseConnection) -> bool:
    """Render login form and update session state."""
    ensure_default_admin(db)
    logo_html = ""
    if LOGO_PATH.exists():
        logo_data = b64encode(LOGO_PATH.read_bytes()).decode("ascii")
        logo_html = f"<img class='crm-login-logo' src='data:image/png;base64,{logo_data}' />"

    left, center, right = st.columns([1, 1.4, 1])
    with center:
        st.markdown(
            f"""
            <div class="crm-login-shell">
                <div class="crm-login-card">
                    {logo_html}
                    <div class="crm-login-title">FitTree CRM</div>
                    <div class="crm-login-subtitle">Sign in to manage leads, follow-ups, and sales activity.</div>
                    <div style="margin-top:1.5rem;text-align:left;">
            """,
            unsafe_allow_html=True,
        )
        with st.form("login_form"):
            st.text_input("Username", key="login_username", placeholder="Enter your username")
            st.text_input("Password", type="password", key="login_password", placeholder="Enter your password")
            st.markdown("<br>", unsafe_allow_html=True)
            submitted = st.form_submit_button("Sign In", use_container_width=True)
        st.markdown(
            """
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    if not submitted:
        return False

    username = st.session_state.get("login_username", "")
    password = st.session_state.get("login_password", "")
    with db.session_scope() as session:
        user = session.scalar(
            select(User).where(User.username == username, User.is_active.is_(True), User.deleted_at.is_(None))
        )
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
