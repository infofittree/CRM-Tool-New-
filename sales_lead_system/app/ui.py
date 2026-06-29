"""Shared Streamlit UI helpers — modern design system components."""

from __future__ import annotations

from base64 import b64encode
from html import escape
from pathlib import Path

import streamlit as st

from app.assets.theme import KPI_META


APP_ROOT = Path(__file__).resolve().parent
CSS_PATH = APP_ROOT / "assets" / "styles.css"
LOGO_PATH = APP_ROOT / "assets" / "fittree_round_logo.png"
SYSTEM_NAME = "FitTree CRM"


ROLE_ACCESS = {
    "Admin": {
        "Dashboard", "Lead Management", "Followups", "My Workspace",
        "Nurturing Leads", "Analytics", "Sales Team", "Reports",
        "Weekly Review", "Settings", "Data Entry",
    },
    "Manager": {
        "Dashboard", "Lead Management", "Followups", "My Workspace",
        "Nurturing Leads", "Analytics", "Sales Team", "Reports",
        "Weekly Review", "Data Entry",
    },
    "Salesperson": {
        "Dashboard", "Lead Management", "Followups", "My Workspace",
        "Nurturing Leads", "Reports", "Weekly Review", "Data Entry",
    },
}


def configure_page(title: str) -> None:
    """Apply global Streamlit page styling."""
    page_icon = str(LOGO_PATH) if LOGO_PATH.exists() else None
    st.set_page_config(page_title=title, page_icon=page_icon, layout="wide")
    if LOGO_PATH.exists() and hasattr(st, "logo"):
        st.logo(str(LOGO_PATH), icon_image=str(LOGO_PATH), size="large")
    if CSS_PATH.exists():
        st.markdown(f"<style>{CSS_PATH.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def require_login(page_name: str) -> dict:
    """Block page rendering if user is unauthenticated or unauthorized."""
    if not st.session_state.get("authenticated"):
        st.warning("Please log in from the Dashboard page.")
        st.stop()
    user = st.session_state["user"]
    allowed = ROLE_ACCESS.get(user["role"], set())
    if page_name not in allowed:
        st.error("You do not have access to this page.")
        st.stop()
    render_sidebar(user)
    return user


def render_sidebar(user: dict) -> None:
    """Render user context and logout button."""
    with st.sidebar:
        render_brand_header()
        st.markdown(
            f"""
            <div style="display:flex;align-items:center;justify-content:space-between;
                        padding:0.75rem 0.5rem 0.5rem;border-bottom:1px solid var(--crm-border);
                        margin-bottom:0.75rem;">
                <div>
                    <div style="font-size:0.7rem;color:var(--crm-muted);text-transform:uppercase;
                                letter-spacing:0.3px;font-weight:700;">Signed in</div>
                    <div style="font-weight:700;color:var(--crm-text);font-size:0.88rem;">
                        {escape(user.get('full_name', user['username']))}</div>
                    <div style="font-size:0.75rem;color:var(--crm-primary);font-weight:600;">
                        {escape(user['role'])}</div>
                </div>
                <div style="width:36px;height:36px;border-radius:50%;
                            background:linear-gradient(135deg,var(--crm-primary),var(--crm-accent));
                            color:white;display:grid;place-items:center;font-weight:800;font-size:0.9rem;">
                    {escape(user.get('full_name', user['username'])[0].upper())}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Logout", use_container_width=True, type="secondary"):
            st.session_state.clear()
            st.rerun()


def render_brand_header() -> None:
    """Render the CRM brand block in the sidebar."""
    if LOGO_PATH.exists():
        logo_data = b64encode(LOGO_PATH.read_bytes()).decode("ascii")
        st.markdown(
            f"""
            <div class="crm-brand">
                <img src="data:image/png;base64,{logo_data}" />
                <div>
                    <div class="crm-brand-title">{SYSTEM_NAME}</div>
                    <div class="crm-brand-subtitle">Sales Lead Master Tracker</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(f"### {SYSTEM_NAME}")


def page_header(title: str, subtitle: str, eyebrow: str = "CRM Workspace") -> None:
    """Render a premium page header with decorative accent."""
    st.markdown(
        f"""
        <div class="crm-page-hero">
            <div>
                <div class="crm-eyebrow">{escape(eyebrow)}</div>
                <div class="crm-page-title">{escape(title)}</div>
                <div class="crm-page-subtitle">{escape(subtitle)}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_header(title: str, subtitle: str | None = None) -> None:
    """Render a reusable section heading."""
    subtitle_html = f"<div class='crm-section-subtitle'>{escape(subtitle)}</div>" if subtitle else ""
    st.markdown(
        f"<div class='crm-section-title'>{escape(title)}</div>{subtitle_html}",
        unsafe_allow_html=True,
    )


def section_card(content: str, title: str | None = None) -> None:
    """Render content inside a glass card section wrapper."""
    title_html = f"<div class='crm-section-title'>{escape(title)}</div>" if title else ""
    st.markdown(
        f"<div class='crm-section'>{title_html}{content}</div>",
        unsafe_allow_html=True,
    )


def empty_state(title: str, message: str) -> None:
    """Render an aesthetic empty state."""
    st.markdown(
        f"""
        <div class="crm-empty">
            <div>
                <div class="crm-empty-title">{escape(title)}</div>
                <div>{escape(message)}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def status_pill(value: str | None) -> str:
    """Return HTML for a CRM status badge."""
    label = str(value or "UNKNOWN").upper()
    css = "status-" + label.lower().replace(" ", "-")
    return f"<span class='crm-pill {css}'>{escape(label)}</span>"


def priority_pill(value: str | None) -> str:
    """Return HTML for a lead priority badge."""
    label = str(value or "MEDIUM").upper()
    css = "priority-" + label.lower()
    return f"<span class='crm-pill {css}'>{escape(label)}</span>"


def score_badge(score: float | int | None, band: str | None = None) -> str:
    """Return HTML for a lead-score badge with HOT/WARM/NURTURE/COLD color."""
    try:
        value = float(score) if score is not None else 0.0
    except (TypeError, ValueError):
        value = 0.0
    if band is None:
        if value >= 90:
            band = "HOT"
        elif value >= 70:
            band = "WARM"
        elif value >= 50:
            band = "NURTURE"
        else:
            band = "COLD"
    emoji = {"HOT": "🔥", "WARM": "🟠", "NURTURE": "🟡", "COLD": "🔵"}.get(band, "")
    css = "score-" + band.lower()
    return f"<span class='crm-pill {css}'>{emoji} {int(round(value))} &middot; {escape(band)}</span>"


def kpi_row(metrics: list[tuple[str, str | int | float, str | None]]) -> None:
    """Render a row of KPI cards with gradient accent bars."""
    cards = []
    for label, value, delta in metrics:
        icon, color = KPI_META.get(label, ("", "#4F46E5"))
        delta_html = f"<div class='crm-kpi-delta'>{escape(str(delta))}</div>" if delta else ""
        cards.append(
            f"<div class='crm-kpi-card' style='--kpi-color:{color}'>"
            "<div class='crm-kpi-head'>"
            f"<div class='crm-kpi-label'>{escape(str(label))}</div>"
            f"<div class='crm-kpi-icon'>{escape(icon)}</div>"
            "</div>"
            f"<div class='crm-kpi-value'>{escape(str(value))}</div>"
            f"{delta_html}"
            "</div>"
        )
    st.markdown(f"<div class='crm-kpi-grid'>{''.join(cards)}</div>", unsafe_allow_html=True)


def metric_card(label: str, value: str | int | float, color: str = "#4F46E5") -> str:
    """Return HTML for a compact inline metric card."""
    return (
        f"<div class='crm-kpi-compact' style='--kpi-color:{color}'>"
        f"<div class='crm-kpi-compact-label'>{escape(str(label))}</div>"
        f"<div class='crm-kpi-compact-value'>{escape(str(value))}</div>"
        f"</div>"
    )


def render_metric_row(metrics: list[tuple[str, str | int | float, str]]) -> None:
    """Render a horizontal row of compact metric cards."""
    cards = "".join(metric_card(label, value, color) for label, value, color in metrics)
    st.markdown(
        f"<div style='display:flex;flex-wrap:wrap;gap:0.5rem;margin-bottom:0.8rem;'>{cards}</div>",
        unsafe_allow_html=True,
    )


def data_table(df, **kwargs) -> None:
    """Render a DataFrame inside the crm-table-shell wrapper."""
    st.markdown("<div class='crm-table-shell'>", unsafe_allow_html=True)
    st.dataframe(df, use_container_width=True, hide_index=True, **kwargs)
    st.markdown("</div>", unsafe_allow_html=True)
