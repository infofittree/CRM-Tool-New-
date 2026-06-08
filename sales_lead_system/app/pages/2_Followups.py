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

today = date.today()


def render_task(service: CRMService, task: dict, prefix: str = "t") -> None:
    """Render one task card with Mark Done / Reschedule / Add Note actions.

    ``prefix`` namespaces widget keys so the same lead can appear in more than
    one tab (e.g. overdue leads show in both Today and Missed) without colliding.
    """
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
            <div class="crm-task-action">▶ {task['recommended_action']} &nbsp;·&nbsp; <span style="color:#64748b">{task['due_label']}</span></div>
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
            service.reschedule_followup(task["lead_id"], new_date, user, note="Rescheduled from task list")
            clear_data_cache()
            st.success(f"Rescheduled to {new_date}.")
            st.rerun()
        note = st.text_input("Add a note", key=f"note_{key}")
        if st.button("📝 Add Note", key=f"addnote_{key}", use_container_width=True):
            if note.strip():
                service.append_note(task["lead_id"], note.strip(), user)
                clear_data_cache()
                st.success("Note added.")
                st.rerun()
            else:
                st.warning("Type a note first.")


from app.db import load_tasks
_tasks_cached = load_tasks(user["role"], user["full_name"], 7, 40)
with db.session_scope() as session:
    service = CRMService(session)
    tasks = _tasks_cached
    s = tasks["summary"]

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Actionable Today", s["actionable_today"])
    m2.metric("Overdue (Missed)", s["overdue"])
    m3.metric("Upcoming (7d)", s["upcoming"])
    m4.metric("Hot / Warm", f"{s['hot']} / {s['warm']}")

    tab_today, tab_upcoming, tab_missed = st.tabs(
        [f"🔴 Today's Tasks ({s['actionable_today']})", f"🗓️ Upcoming ({s['upcoming']})", f"⚠️ Missed / Overdue ({s['overdue']})"]
    )

    with tab_today:
        st.caption("Everything needing action now — overdue + due today, highest score first. Completing a task removes it from this list.")
        if s["overflow"]:
            st.info(f"Showing top {s['capped_shown']} by priority. {s['overflow']} more queued — clear these first to protect focus.")
        if not tasks["today_capped"]:
            empty_state("All caught up", "No tasks need action today.")
        for task in tasks["today_capped"]:
            render_task(service, task, prefix="today")

    with tab_upcoming:
        st.caption("Scheduled within the next 7 days (tomorrow → +7).")
        if not tasks["upcoming"]:
            empty_state("Nothing upcoming", "No future-dated follow-ups in the next 7 days.")
        for task in tasks["upcoming"][:40]:
            render_task(service, task, prefix="upcoming")

    with tab_missed:
        st.caption("Overdue items — these also appear in Today's Tasks but are flagged here for visibility.")
        if not tasks["overdue"]:
            empty_state("Nothing overdue", "No missed follow-ups.")
        for task in tasks["overdue"][:40]:
            render_task(service, task, prefix="missed")
