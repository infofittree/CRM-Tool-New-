"""Main Streamlit CRM dashboard — task-execution focused."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import plotly.express as px
import streamlit as st

from app.assets.theme import STATUS_COLORS, style_plotly
from app.db import ensure_startup, get_db, render_startup_status
from app.login import render_login
from app.ui import configure_page, empty_state, page_header, render_sidebar, score_badge, section_header, status_pill
from modules import dashboard_queries
from modules.crm_service import CRMService
from modules.status_taxonomy import FUNNEL_ORDER

configure_page("Sales CRM Dashboard")
db = get_db()
startup_status = ensure_startup(db)
if startup_status.errors:
    st.error(startup_status.errors[0])
    st.stop()

if not st.session_state.get("authenticated"):
    render_login(db)
    st.stop()

user = st.session_state["user"]
render_sidebar(user)
render_startup_status(startup_status)

page_header(
    "Sales CRM Dashboard",
    "Today's tasks, pipeline health, follow-ups, and team performance — live.",
    "Sales Operating System",
)

today = date.today()

with db.session_scope() as session:
    service = CRMService(session)
    metrics = service.dashboard_metrics(user)
    leads_df = service.leads_dataframe(user, limit=5000)
    tasks = service.get_tasks(user, upcoming_days=7, max_today=40)
    ts = tasks["summary"]
    engagement = dashboard_queries.get_engagement_stats(session, user, days=7)
    performance_df = dashboard_queries.get_salesperson_stats(session, user)
    activity_df = dashboard_queries.get_recent_activities(session)

    # Band counts from live scores
    bands = {"HOT": 0, "WARM": 0, "NURTURE": 0, "COLD": 0}
    if not leads_df.empty and "lead_score" in leads_df.columns:
        for sc in leads_df["lead_score"].fillna(0):
            sc = float(sc)
            key = "HOT" if sc >= 90 else "WARM" if sc >= 70 else "NURTURE" if sc >= 50 else "COLD"
            bands[key] += 1

    negotiation_n = int((leads_df.get("standard_status") == "Negotiation").sum()) if not leads_df.empty else 0
    completion = round(engagement["today_done"] / (engagement["today_done"] + ts["actionable_today"]) * 100, 0) if (engagement["today_done"] + ts["actionable_today"]) else 0

    # ---------------- TOP KPIs ----------------
    from app.ui import kpi_row
    kpi_row([
        ("Today's Tasks", ts["actionable_today"], "to action now"),
        ("Overdue", ts["overdue"], "missed follow-ups"),
        ("Upcoming 7d", ts["upcoming"], "scheduled"),
        ("Hot Leads", bands["HOT"], "🔥 90+"),
        ("Negotiation", negotiation_n, "in pipeline"),
        ("Nurturing", metrics["nurturing"], "warm pipeline"),
        ("Converted", metrics["converted"], "won"),
        ("Task Completion", f"{int(completion)}%", f"{engagement['today_done']} done today"),
    ])

    st.divider()

    # ---------------- TODAY'S PRIORITY TASKS ----------------
    section_header("Today's Priority Tasks", "Highest-scoring leads needing action now — who, why, how, when.")
    if not tasks["today_capped"]:
        empty_state("All caught up", "No tasks need action today. Check Upcoming on the Follow-ups page.")
    else:
        if ts["overflow"]:
            st.info(f"Showing top {ts['capped_shown']} of {ts['actionable_today']} by priority. Open the Follow-ups page to work the full queue.")
        for task in tasks["today_capped"][:12]:
            band = task["band"].lower()
            cols = st.columns([5, 2, 2])
            with cols[0]:
                st.markdown(
                    f"""
                    <div class="crm-task task-{band}">
                        <div class="crm-task-head">
                            <span class="crm-task-company">{task['company_name']}</span>
                            <span>{score_badge(task['score'], task['band'])} {status_pill(task['standard_status'])}</span>
                        </div>
                        <div class="crm-task-action">▶ {task['recommended_action']} · <span style="color:#64748b">{task['due_label']}</span></div>
                        <div class="crm-task-reason">{task['reason']} <span class='crm-pill category-{task.get('lead_category','C').lower()}'>{task.get('lead_category','C')}</span></div>
                        <div class="crm-task-meta">📋 {task.get('next_action_plan') or 'No action plan set'}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with cols[1]:
                st.caption("Contact")
                st.write(task.get("phone") or task.get("whatsapp_number") or task.get("email") or "—")
            with cols[2]:
                if st.button("✅ Mark Done", key=f"dash_done_{task['lead_id']}", use_container_width=True):
                    from datetime import timedelta
                    service.add_quick_followup(
                        task["lead_id"],
                        {"discussion": "Task completed from dashboard", "next_action": task["recommended_action"],
                         "next_followup": today + timedelta(days=3), "mode": task.get("mode")},
                        user,
                    )
                    st.rerun()

    st.divider()

    # ---------------- FOLLOW-UP WIDGETS + FUNNEL ----------------
    left, right = st.columns([1.25, 1])
    with left:
        section_header("Lead Funnel", "Pipeline across the standard sales stages.")
        status_col = "standard_status" if "standard_status" in leads_df.columns else "status"
        if leads_df.empty:
            empty_state("No leads found", "Import or add leads to build the funnel.")
        else:
            funnel = leads_df.groupby(status_col, dropna=False).size().reset_index()
            funnel.columns = ["status", "count"]
            funnel = funnel[funnel["status"].isin(FUNNEL_ORDER) & (funnel["count"] > 0)].copy()
            funnel["__o"] = funnel["status"].map({s: i for i, s in enumerate(FUNNEL_ORDER)})
            funnel = funnel.sort_values("__o")
            fig = px.funnel(funnel, x="count", y="status", color="status", color_discrete_map=STATUS_COLORS)
            fig = style_plotly(fig, height=380)
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    with right:
        section_header("Pipelines", "Negotiation and nurturing queues.")
        st.metric("Negotiation Pipeline", negotiation_n)
        st.metric("Nurturing Pipeline", metrics["nurturing"])
        st.metric("Missed Follow-ups", ts["overdue"])
        st.metric("Upcoming (7d)", ts["upcoming"])

    st.divider()

    # ---------------- LEAD QUALITY ----------------
    section_header("Lead Quality Analysis", "Score-band distribution and top geographies.")
    q1, q2, q3, q4 = st.columns(4)
    q1.metric("🔥 Hot", bands["HOT"])
    q2.metric("🟠 Warm", bands["WARM"])
    q3.metric("🟡 Nurture", bands["NURTURE"])
    q4.metric("🔵 Cold", bands["COLD"])
    geo1, geo2 = st.columns(2)
    if not leads_df.empty and "country" in leads_df.columns:
        top_countries = leads_df["country"].dropna().value_counts().head(8).reset_index()
        top_countries.columns = ["country", "leads"]
        geo1.plotly_chart(style_plotly(px.bar(top_countries, x="country", y="leads", title="Top Countries"), height=320), use_container_width=True)
    if not leads_df.empty and "continent" in leads_df.columns:
        by_cont = leads_df["continent"].dropna().value_counts().reset_index()
        by_cont.columns = ["continent", "leads"]
        geo2.plotly_chart(style_plotly(px.pie(by_cont, names="continent", values="leads", title="Leads by Continent"), height=320), use_container_width=True)

    # Lead Source analytics (Patch 5)
    if not leads_df.empty and "lead_source" in leads_df.columns:
        section_header("Lead Source Analytics", "Where leads come from and which sources convert.")
        src1, src2 = st.columns(2)
        by_src = leads_df["lead_source"].dropna().value_counts().reset_index()
        by_src.columns = ["source", "leads"]
        src1.plotly_chart(style_plotly(px.bar(by_src, x="source", y="leads", title="Leads by Source"), height=300), use_container_width=True)
        won = leads_df[leads_df["standard_status"] == "Order Closed"] if "standard_status" in leads_df.columns else leads_df.iloc[0:0]
        if not won.empty:
            wsrc = won["lead_source"].dropna().value_counts().reset_index()
            wsrc.columns = ["source", "orders_closed"]
            src2.plotly_chart(style_plotly(px.bar(wsrc, x="source", y="orders_closed", title="Orders Closed by Source"), height=300), use_container_width=True)
        else:
            src2.info("Orders-closed-by-source will populate as deals close.")

    # Alibaba Buyer Level analytics (Patch — only when Alibaba leads exist)
    if not leads_df.empty and "lead_source" in leads_df.columns:
        ali = leads_df[leads_df["lead_source"] == "Alibaba"].copy()
        if not ali.empty and "buyer_tag" in ali.columns and ali["buyer_tag"].notna().any():
            section_header("Alibaba Buyer Quality", "Buyer-level distribution and conversion (Alibaba leads only).")
            al1, al2 = st.columns(2)
            lvl = ali["buyer_tag"].fillna("Unrated").value_counts().reindex(["L4", "L3", "L2", "L1", "Unrated"]).dropna().reset_index()
            lvl.columns = ["level", "count"]
            al1.plotly_chart(style_plotly(px.bar(lvl, x="level", y="count", title="Alibaba Buyer Level Distribution",
                            color="level", color_discrete_map={"L4": "#15803d", "L3": "#65a30d", "L2": "#f59e0b", "L1": "#ef4444"}).update_layout(showlegend=False), height=300), use_container_width=True)
            if "standard_status" in ali.columns:
                conv = ali.groupby("buyer_tag").apply(
                    lambda g: round((g["standard_status"] == "Order Closed").sum() / len(g) * 100, 1), include_groups=False
                ).reindex(["L4", "L3", "L2", "L1"]).dropna().reset_index()
                conv.columns = ["level", "closed_pct"]
                if not conv.empty:
                    al2.plotly_chart(style_plotly(px.bar(conv, x="level", y="closed_pct", title="Conversion % by Alibaba Level"), height=300), use_container_width=True)

    st.divider()

    # ---------------- SALES TEAM PERFORMANCE ----------------
    perf_col, act_col = st.columns([1, 1])
    with perf_col:
        section_header("Sales Team Performance", "Assignments, conversions, and 7-day activity.")
        if performance_df.empty:
            empty_state("No salesperson data", "Assign leads to build the leaderboard.")
        else:
            perf = performance_df.copy()
            perf["activity_7d"] = perf["assigned_to"].map(engagement["by_user"]).fillna(0).astype(int)
            st.dataframe(perf.sort_values("assigned_leads", ascending=False), use_container_width=True, hide_index=True)
        a1, a2, a3 = st.columns(3)
        a1.metric("Calls (7d)", engagement["calls"])
        a2.metric("WhatsApp (7d)", engagement["whatsapp"])
        a3.metric("Follow-ups (7d)", engagement["followups"])
    with act_col:
        section_header("Recent Activity", "Latest audit trail from imports and actions.")
        if activity_df.empty:
            empty_state("No activity yet", "Activity appears after imports, edits, and follow-ups.")
        else:
            st.markdown("<div class='crm-timeline'>", unsafe_allow_html=True)
            for row in activity_df.head(8).itertuples():
                st.markdown(
                    f"""
                    <div class="crm-timeline-item">
                        <div class="crm-timeline-title">{row.action}</div>
                        <div class="crm-timeline-meta">{row.timestamp} | {row.user_name or 'system'} | {row.lead_id or ''}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            st.markdown("</div>", unsafe_allow_html=True)
