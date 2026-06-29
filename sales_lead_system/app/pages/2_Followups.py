"""Follow-up & task execution page — driven by the smart task engine."""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st

from app.db import ensure_startup, get_db, render_startup_status
from app.ui import configure_page, empty_state, page_header, require_login, score_badge, status_pill
from modules.clock import today as biz_today
from modules.crm_service import CRMService

configure_page("Follow-ups")
user = require_login("Followups")
page_header("Follow-up & Tasks", "Everything that needs action today, what is overdue, and what is coming up.", "Follow-up Engine")

db = get_db()
startup_status = ensure_startup(db)
render_startup_status(startup_status)
if startup_status.errors:
    st.error(startup_status.errors[0])
    st.stop()

today = biz_today()


def render_task(service: CRMService, task: dict, prefix: str = "t") -> None:
    """Render one task card with Mark Done / Reschedule / Add Note actions."""
    key = f"{prefix}_{task['lead_id']}"
    band = task["band"].lower()
    contact_bits = []
    if task.get("phone"):
        contact_bits.append(f"☎ {task['phone']}")
    if task.get("whatsapp_number"):
        contact_bits.append(f"WA {task['whatsapp_number']}")
    if task.get("email"):
        contact_bits.append(f"✉ {task['email']}")
    contact_line = "  |  ".join(contact_bits) or "No contact details"

    st.markdown(
        f"""
        <div class="crm-task task-{band}">
            <div class="crm-task-head">
                <span class="crm-task-company">{task['company_name']}</span>
                <span>{score_badge(task['score'], task['band'])} {status_pill(task['standard_status'])}</span>
            </div>
            <div class="crm-task-action">▶ {task['recommended_action']} &nbsp;·&nbsp; <span style="color:var(--crm-muted)">{task['due_label']}</span></div>
            <div class="crm-task-reason">{task['reason']}</div>
            <div class="crm-task-meta">{contact_line}</div>
            <div class="crm-task-meta">Last contact: {task['last_contact_date'] or '—'} &nbsp;|&nbsp; 📋 {task.get('next_action_plan') or 'No action plan set'}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.expander("Action"):
        from app.db import clear_data_cache
        c1, c2 = st.columns(2)
        if c1.button("✅ Mark Done", key=f"done_{key}", use_container_width=True):
            service.add_quick_followup(
                task["lead_id"],
                {"discussion": "Task completed", "next_action": task["recommended_action"],
                 "next_followup": today + timedelta(days=3), "mode": task.get("mode")},
                user,
            )
            clear_data_cache()
            st.success("Marked done. Next touch scheduled in 3 days.")
            st.rerun()
        new_date = c2.date_input("Reschedule to", value=today + timedelta(days=2), key=f"resdate_{key}")
        if c2.button("📅 Reschedule", key=f"res_{key}", use_container_width=True):
            service.add_quick_followup(
                task["lead_id"],
                {"discussion": f"Rescheduled from {task['due_label']}", "next_action": task["recommended_action"],
                 "next_followup": new_date, "mode": task.get("mode")},
                user,
            )
            clear_data_cache()
            st.success(f"Rescheduled to {new_date}.")
            st.rerun()
        if c1.button("📝 Add Note", key=f"note_{key}", use_container_width=True):
            st.session_state[f"note_text_{key}"] = True
        if st.session_state.get(f"note_text_{key}"):
            note = st.text_area("Note", key=f"ntext_{key}", placeholder="What happened?")
            if st.button("Save Note", key=f"nsave_{key}"):
                service.add_quick_followup(
                    task["lead_id"],
                    {"discussion": note, "next_action": task["recommended_action"],
                     "next_followup": new_date if 'new_date' in dir() else today + timedelta(days=3),
                     "mode": task.get("mode")},
                    user,
                )
                st.session_state.pop(f"note_text_{key}", None)
                clear_data_cache()
                st.success("Note saved.")
                st.rerun()


db = get_db()
startup_status = ensure_startup(db)
render_startup_status(startup_status)
if startup_status.errors:
    st.error(startup_status.errors[0])
    st.stop()

from app.db import load_tasks
tasks = load_tasks(user["role"], user["full_name"], 14, 200)
ts = tasks["summary"]

kpi_col1, kpi_col2, kpi_col3, kpi_col4, kpi_col5 = st.columns(5)
kpi_col1.markdown(f"<div style='background:var(--crm-card);border:1px solid var(--crm-border);border-radius:12px;padding:0.7rem;text-align:center;'><div style='font-size:1.4rem;font-weight:850;color:var(--crm-text);'>{ts['actionable_today']}</div><div style='font-size:0.7rem;color:var(--crm-muted);text-transform:uppercase;letter-spacing:0.3px;font-weight:700;'>Today</div></div>", unsafe_allow_html=True)
kpi_col2.markdown(f"<div style='background:var(--crm-card);border:1px solid var(--crm-border);border-radius:12px;padding:0.7rem;text-align:center;'><div style='font-size:1.4rem;font-weight:850;color:var(--crm-danger);'>{ts['overdue']}</div><div style='font-size:0.7rem;color:var(--crm-muted);text-transform:uppercase;letter-spacing:0.3px;font-weight:700;'>Overdue</div></div>", unsafe_allow_html=True)
kpi_col3.markdown(f"<div style='background:var(--crm-card);border:1px solid var(--crm-border);border-radius:12px;padding:0.7rem;text-align:center;'><div style='font-size:1.4rem;font-weight:850;color:var(--crm-text);'>{ts['upcoming']}</div><div style='font-size:0.7rem;color:var(--crm-muted);text-transform:uppercase;letter-spacing:0.3px;font-weight:700;'>Upcoming</div></div>", unsafe_allow_html=True)
kpi_col4.markdown(f"<div style='background:var(--crm-card);border:1px solid var(--crm-border);border-radius:12px;padding:0.7rem;text-align:center;'><div style='font-size:1.4rem;font-weight:850;color:var(--crm-text);'>{ts['capped_shown']}</div><div style='font-size:0.7rem;color:var(--crm-muted);text-transform:uppercase;letter-spacing:0.3px;font-weight:700;'>Showing</div></div>", unsafe_allow_html=True)
kpi_col5.markdown(f"<div style='background:var(--crm-card);border:1px solid var(--crm-border);border-radius:12px;padding:0.7rem;text-align:center;'><div style='font-size:1.4rem;font-weight:850;color:var(--crm-text);'>{ts['overflow']}</div><div style='font-size:0.7rem;color:var(--crm-muted);text-transform:uppercase;letter-spacing:0.3px;font-weight:700;'>Overflow</div></div>", unsafe_allow_html=True)

tabs = st.tabs(["📋 Today", "⏰ Overdue", "📅 Upcoming (7d)", "🗓️ All (14d)"])

with db.session_scope() as session:
    service = CRMService(session)

    with tabs[0]:
        if not tasks["today_capped"]:
            empty_state("All caught up", "No tasks need action today.")
        else:
            for task in tasks["today_capped"]:
                render_task(service, task, "tod")

    with tabs[1]:
        if not tasks["overdue_list"]:
            empty_state("Nothing overdue", "Great work staying on top.")
        else:
            for task in tasks["overdue_list"]:
                render_task(service, task, "ovr")

    with tabs[2]:
        if not tasks["upcoming_list"]:
            empty_state("Nothing upcoming", "Check back after scheduling more follow-ups.")
        else:
            for task in tasks["upcoming_list"]:
                render_task(service, task, "upc")

    with tabs[3]:
        if not tasks["all_list"]:
            empty_state("No tasks in the next 14 days", "Schedule follow-ups to build the queue.")
        else:
            for task in tasks["all_list"]:
                render_task(service, task, "all")
