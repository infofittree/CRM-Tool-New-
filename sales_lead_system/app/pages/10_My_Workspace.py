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
        stage = st.selectbox("Stage", list(CANONICAL_STATUSES),
                             index=list(CANONICAL_STATUSES).index(new_stage) if new_stage in CANONICAL_STATUSES else 0,
                             key=f"qs_{lid}")
        is_lost = stage == "Lost"
        next_fu = None
        plan = ""
        lost_reason = "—"
        if is_lost:
            # Phase 5: Lost needs only a reason — no follow-up / action plan / notes
            lost_reason = st.selectbox("Lost Reason *", ["—"] + _LOST_REASONS, key=f"ql_{lid}")
            notes = st.text_input("Notes (optional)", key=f"qn_{lid}")
            st.caption("Lost leads only need a reason — no follow-up required.")
        else:
            next_fu = st.date_input("Next Follow-up *", value=today + timedelta(days=2),
                                    min_value=today, max_value=today + timedelta(days=30), key=f"qf_{lid}")
            plan = st.text_input("Next Action Plan *", key=f"qp_{lid}", placeholder="e.g. Call for quotation feedback")
            notes = st.text_input("Notes (optional)", key=f"qn_{lid}", placeholder="e.g. Buyer requested revised price")
        if st.button("✅ Save", key=f"qb_{lid}", use_container_width=True):
            errs = []
            if is_lost:
                if lost_reason == "—":
                    errs.append("Lost reason")
            else:
                if not next_fu:
                    errs.append("Next follow-up date")
                if not plan.strip():
                    errs.append("Next action plan")
            if errs:
                st.error("Required: " + ", ".join(errs))
            else:
                service.add_quick_followup(
                    lid,
                    {"discussion": notes or action, "next_action": plan or action, "next_followup": next_fu,
                     "status": stage, "lost_reason": None if lost_reason == "—" else lost_reason},
                    user,
                )
                from app.db import clear_data_cache
                clear_data_cache()
                st.success("✅ Updated.")
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
    # Per-lead contact lookup (full details for the card) from the leads dataframe.
    contact = {}
    if not leads.empty and "lead_id" in leads.columns:
        contact = leads.set_index("lead_id").to_dict("index")

    # ---- Today's priority work — full-width, larger cards with contact details ----
    section_header("Today's Priority Work", f"Top {s['capped_shown']} tasks, smart-sorted. {s['overflow']} more queued.")
    if not tasks["today_capped"]:
        empty_state("All clear", "No tasks need action today.")
    for t in tasks["today_capped"]:
        band = t["band"].lower()
        c = contact.get(t["lead_id"], {})
        contact_person = c.get("contact_person") or "—"
        email = c.get("email") or t.get("email") or "—"
        phone = c.get("phone") or t.get("phone") or "—"
        country = c.get("country") or t.get("country") or "—"
        continent = c.get("continent") or "—"
        st.markdown(
            f"""<div class="crm-task crm-task-lg task-{band}">
            <div class="crm-task-head">
                <span class="crm-task-company">{t['company_name']} <span class='crm-pill category-{t['lead_category'].lower()}'>{t['lead_category']}</span></span>
                <span>{score_badge(t['score'], t['band'])} {status_pill(t['standard_status'])}</span>
            </div>
            <div class="crm-contact-grid">
                <div>👤 <b>{contact_person}</b></div>
                <div>☎ {phone}</div>
                <div>✉ {email}</div>
                <div>🌍 {country}{(' · ' + continent) if continent != '—' else ''}</div>
            </div>
            <div class="crm-task-action">▶ {t['recommended_action']} · <span style="color:#64748b">{t['due_label']}</span></div>
            <div class="crm-task-reason">{t['reason']}</div>
            <div class="crm-task-meta">📋 Plan: {t['next_action_plan'] or '—'} &nbsp;|&nbsp; {t.get('product_interest') or ''}</div>
            </div>""",
            unsafe_allow_html=True,
        )
        _quick_action(service, t, user)

    st.divider()
    # ---- Overdue list ----
    section_header("⚠️ My Overdue Leads", "These slipped — clear them first.")
    if not tasks["overdue"]:
        empty_state("Nothing overdue", "Great — you're on top of your follow-ups.")
    else:
        odf = pd.DataFrame(tasks["overdue"])[["company_name", "standard_status", "lead_category", "score", "due_label", "next_action_plan"]]
        st.dataframe(odf, use_container_width=True, hide_index=True)
