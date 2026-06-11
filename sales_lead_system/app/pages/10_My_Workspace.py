"""Salesperson Workspace — each rep sees only their own work, clearly."""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pandas as pd
import plotly.express as px
import streamlit as st

from app.assets.theme import STATUS_COLORS, style_plotly
from app.db import ensure_startup, get_db, render_startup_status
from app.ui import configure_page, empty_state, page_header, require_login, score_badge, section_header, status_pill
from modules.clock import today as biz_today
from modules.crm_service import CRMService
from modules.status_taxonomy import FUNNEL_ORDER

configure_page("My Workspace")
user = require_login("My Workspace")
page_header("My Workspace", "Your companies, your follow-ups, your priorities — nothing else.", "Salesperson Desk")

db = get_db()
startup_status = ensure_startup(db)
render_startup_status(startup_status)
if startup_status.errors:
    st.error(startup_status.errors[0])
    st.stop()

today = biz_today()

from modules.status_taxonomy import CANONICAL_STATUSES
from modules.dropdown_config import option_list

_QUICK_ACTIONS = [
    "— pick action —", "Follow-Up Done", "Customer Responded", "Stage Updated",
    "Move to Nurturing", "Mark Lost", "Task Completed", "Mark Done For Today",
]
_LOST_REASONS = option_list("lost_reasons")


def _quick_action(service: CRMService, t: dict, user: dict) -> None:
    """Fast inline update — next follow-up + action plan mandatory, <10s."""
    lid = t["lead_id"]
    with st.expander("⚡ Quick action"):
        action = st.selectbox("Action", _QUICK_ACTIONS, key=f"qa_{lid}")
        if action == "— pick action —":
            return
        # Action-driven status default
        status_map = {"Move to Nurturing": "Nurturing", "Mark Lost": "Lost"}
        new_stage = status_map.get(action, t["standard_status"])
        cols = st.columns(2)
        next_fu = cols[0].date_input("Next Follow-up *", value=today + timedelta(days=2),
                                     min_value=today, max_value=today + timedelta(days=30), key=f"qf_{lid}")
        stage = cols[1].selectbox("Stage", list(CANONICAL_STATUSES),
                                  index=list(CANONICAL_STATUSES).index(new_stage) if new_stage in CANONICAL_STATUSES else 0,
                                  key=f"qs_{lid}")
        plan = st.text_input("Next Action Plan *", key=f"qp_{lid}", placeholder="e.g. Call for quotation feedback")
        notes = st.text_input("Notes *", key=f"qn_{lid}", placeholder="e.g. Buyer requested revised price")
        lost_reason = "—"
        if stage == "Lost":
            lost_reason = st.selectbox("Lost Reason *", ["—"] + _LOST_REASONS, key=f"ql_{lid}")
        st.caption("All three (date, notes, action plan) are required — keeps follow-up continuity.")
        if st.button("✅ Save & schedule next", key=f"qb_{lid}", use_container_width=True):
            errs = []
            if not next_fu:
                errs.append("Next follow-up date")
            if not notes.strip():
                errs.append("Notes")
            if not plan.strip():
                errs.append("Next action plan")
            if stage == "Lost" and lost_reason == "—":
                errs.append("Lost reason")
            if errs:
                st.error("Required: " + ", ".join(errs))
            else:
                service.add_quick_followup(
                    lid,
                    {"discussion": notes, "next_action": plan, "next_followup": next_fu,
                     "status": stage, "lost_reason": None if lost_reason == "—" else lost_reason},
                    user,
                )
                from app.db import clear_data_cache
                clear_data_cache()
                st.success("✅ Updated — notes logged, next follow-up scheduled.")
                st.rerun()


with db.session_scope() as session:
    service = CRMService(session)
    salespersons = service.get_salespersons()

    # Admin/Manager can pick whose desk to view; Salesperson sees only their own.
    if user["role"] in ("Admin", "Manager"):
        who = st.selectbox("View workspace of", salespersons)
        focus = {"role": "Salesperson", "full_name": who}
    else:
        focus = user
        who = user["full_name"]

    from app.db import load_leads_df, load_tasks
    leads = load_leads_df(focus["role"], focus["full_name"], 5000)
    tasks = load_tasks(focus["role"], focus["full_name"], 7, 20)
    s = tasks["summary"]

    if leads.empty:
        empty_state("No companies assigned", f"{who} has no leads assigned yet.")
        st.stop()

    # ---- KPIs ----
    k = st.columns(5)
    k[0].metric("My Companies", len(leads))
    k[1].metric("Today's Tasks", s["actionable_today"])
    k[2].metric("Overdue", s["overdue"])
    k[3].metric("Upcoming 7d", s["upcoming"])
    k[4].metric("Hot / Warm", f"{s['hot']} / {s['warm']}")

    st.divider()
    left, right = st.columns([1.2, 1])

    # ---- Today's priority work ----
    with left:
        section_header("Today's Priority Work", f"Top {s['capped_shown']} tasks, smart-sorted. {s['overflow']} more queued.")
        if not tasks["today_capped"]:
            empty_state("All clear", "No tasks need action today.")
        for t in tasks["today_capped"]:
            band = t["band"].lower()
            st.markdown(
                f"""<div class="crm-task task-{band}">
                <div class="crm-task-head">
                    <span class="crm-task-company">{t['company_name']} <span class='crm-pill category-{t['lead_category'].lower()}'>{t['lead_category']}</span></span>
                    <span>{score_badge(t['score'], t['band'])} {status_pill(t['standard_status'])}</span>
                </div>
                <div class="crm-task-action">▶ {t['recommended_action']} · <span style="color:#64748b">{t['due_label']}</span></div>
                <div class="crm-task-reason">{t['reason']}</div>
                <div class="crm-task-meta">📋 Plan: {t['next_action_plan'] or '—'}</div>
                <div class="crm-task-meta">{t.get('phone') or t.get('whatsapp_number') or t.get('email') or 'No contact'} · {t.get('product_interest') or ''}</div>
                </div>""",
                unsafe_allow_html=True,
            )
            # ---- QUICK ACTION (fast update, <10s, no full form) ----
            _quick_action(service, t, user)

    # ---- Funnel + recent ----
    with right:
        section_header("My Funnel", "Where my pipeline sits.")
        col = "standard_status" if "standard_status" in leads.columns else "status"
        fd = leads.groupby(col).size().reset_index()
        fd.columns = ["status", "count"]
        fd = fd[fd["status"].isin(FUNNEL_ORDER) & (fd["count"] > 0)]
        if not fd.empty:
            fd["__o"] = fd["status"].map({v: i for i, v in enumerate(FUNNEL_ORDER)})
            fd = fd.sort_values("__o")
            fig = px.bar(fd, x="count", y="status", orientation="h", color="status", color_discrete_map=STATUS_COLORS)
            st.plotly_chart(style_plotly(fig, height=300).update_layout(showlegend=False), use_container_width=True)

        section_header("Recently Assigned", "Newest companies on my desk.")
        recent = leads.sort_values("created_at", ascending=False).head(6) if "created_at" in leads.columns else leads.head(6)
        st.dataframe(recent[["company_name", "standard_status", "lead_score", "country"]] if "standard_status" in recent.columns
                     else recent[["company_name", "status", "country"]],
                     use_container_width=True, hide_index=True)

    st.divider()
    # ---- Overdue list ----
    section_header("⚠️ My Overdue Leads", "These slipped — clear them first.")
    if not tasks["overdue"]:
        empty_state("Nothing overdue", "Great — you're on top of your follow-ups.")
    else:
        odf = pd.DataFrame(tasks["overdue"])[["company_name", "standard_status", "lead_category", "score", "due_label", "next_action_plan"]]
        st.dataframe(odf, use_container_width=True, hide_index=True)
