"""Smart task-derivation engine — new 10-stage funnel (Phase 4).

Key improvements:
  - Priority derived from stage rank × category × overdue urgency (not plain score).
  - Queue size is CAPPED: salesperson sees ≤20 tasks/day by default.
  - Only leads with a follow-up date due (or overdue) within `horizon_days` appear.
  - Leads without any follow-up date use cadence from their stage to determine due date.
  - Nurturing leads enter the queue at their own slower cadence.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from database.models import EngagementEvent, FollowUp, Lead
from modules.lead_scoring import band_emoji, score_lead
from modules.notes_engine import suggest_from_note
from modules.status_taxonomy import (
    STAGE_ACTION, STAGE_CADENCE, STAGE_PRIORITY, TERMINAL_LOST, TERMINAL_WON,
    is_open, to_canonical,
)
from modules.clock import today as _biz_today

# ── Column name cache (avoids repeated SQLAlchemy reflection) ─────────────────
_LEAD_COLUMN_NAMES: list[str] | None = None

def _lead_columns() -> list[str]:
    global _LEAD_COLUMN_NAMES
    if _LEAD_COLUMN_NAMES is None:
        _LEAD_COLUMN_NAMES = [c.name for c in Lead.__table__.columns]
    return _LEAD_COLUMN_NAMES


# ── Sane daily queue limit ───────────────────────────────────────────────────
DEFAULT_MAX_TODAY = 20


def _as_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return datetime.fromisoformat(str(value)[:10]).date()
    except (ValueError, TypeError):
        return None


def _scope(user: dict[str, Any]):
    base = Lead.deleted_at.is_(None)
    if user.get("role") == "Salesperson":
        name = (user.get("full_name") or "").strip()
        return and_(base, Lead.assigned_to.isnot(None), func.lower(Lead.assigned_to) == name.lower())
    return base


def _priority_score(task: dict) -> int:
    """Composite priority: overdue urgency + stage rank + category.

    Higher = shown first.
    """
    # Urgency tier: overdue=3, today=2, tomorrow=1, upcoming=0
    days = task["days_to"]
    urgency = 3 if days < 0 else 2 if days == 0 else 1 if days == 1 else 0

    # Stage urgency (1=highest→8=lowest; invert so 8→highest number)
    stage_score = 9 - STAGE_PRIORITY.get(task["standard_status"], 8)

    # Category weight: A=3, B=2, C=1
    cat = task.get("lead_category") or "C"
    cat_score = {"A": 3, "B": 2, "C": 1}.get(cat.upper(), 1)

    return urgency * 1000 + stage_score * 100 + cat_score * 10


def generate_tasks(
    session: Session,
    user: dict[str, Any],
    *,
    today: date | None = None,
    upcoming_days: int = 7,
    max_today: int = DEFAULT_MAX_TODAY,
) -> dict[str, Any]:
    """Build the live task queue for a user.

    Returns:
        today         list of tasks due today
        overdue       list of overdue tasks
        upcoming      list of tasks due within upcoming_days
        actionable_today  overdue + today (capped to max_today by priority)
        today_capped  the visible slice for the dashboard
        summary       dict of KPI counts
    """
    today = today or _biz_today()

    # Latest follow-up per lead via MAX(followup_id) subquery (single SQL pass)
    latest_fu = (
        select(FollowUp.lead_id, func.max(FollowUp.followup_id).label("max_id"))
        .group_by(FollowUp.lead_id)
    ).subquery()
    fu_next: dict[str, Any] = {}
    fu_notes: dict[str, Any] = {}
    fu_completed_at: dict[str, Any] = {}
    fu_completed_by: dict[str, Any] = {}
    fu_followup_id: dict[str, int] = {}
    fu_discussion: dict[str, str] = {}
    fu_next_action: dict[str, str] = {}
    for lead_id, nf, notes, ca, cb, fid, disc, na in session.execute(
        select(FollowUp.lead_id, FollowUp.next_followup, FollowUp.outcome_notes, FollowUp.completed_at, FollowUp.completed_by, FollowUp.followup_id, FollowUp.discussion, FollowUp.next_action)
        .join(latest_fu, and_(FollowUp.lead_id == latest_fu.c.lead_id, FollowUp.followup_id == latest_fu.c.max_id))
    ):
        fu_next[lead_id] = nf
        fu_notes[lead_id] = notes
        fu_completed_at[lead_id] = ca
        fu_completed_by[lead_id] = cb
        fu_followup_id[lead_id] = fid
        fu_discussion[lead_id] = disc or ""
        fu_next_action[lead_id] = na or ""

    # Pre-load leads using Core (avoids ORM->dict overhead)
    from sqlalchemy import select as sa_select
    leads_table = Lead.__table__
    scope_filter = _scope(user)
    lead_rows = session.execute(
        sa_select(leads_table).where(
            scope_filter,
            leads_table.c.status.notin_([*TERMINAL_LOST, TERMINAL_WON]),
            leads_table.c.deleted_at.is_(None),
        ).order_by(leads_table.c.updated_at.desc()).limit(1000)
    ).all()

    overdue: list[dict] = []
    today_tasks: list[dict] = []
    upcoming: list[dict] = []
    completed_tasks: list[dict] = []

    for row in lead_rows:
        lead = dict(row._mapping)
        canonical = to_canonical(lead.get("status"))
        if not is_open(canonical):
            continue

        score, band, _ = score_lead(lead)
        lid = lead.get("lead_id")

        # Check if this lead's latest follow-up is already completed
        latest_completed = fu_completed_at.get(lid)
        if latest_completed is not None:
            # Keep in completed bucket if within last 7 days
            if isinstance(latest_completed, datetime):
                if (today - latest_completed.date()).days <= 7:
                    completed_tasks.append({
                        "lead_id": lid,
                        "company_name": lead.get("company_name"),
                        "assigned_to": lead.get("assigned_to"),
                        "status": lead.get("status"),
                        "standard_status": canonical,
                        "score": score,
                        "band": band,
                        "band_emoji": band_emoji(band),
                        "lead_category": lead.get("lead_category") or "C",
                        "recommended_action": "Completed",
                        "reason": None,
                        "next_action_plan": None,
                        "due_date": None,
                        "due_label": "Completed",
                        "days_to": 0,
                        "last_contact_date": _as_date(lead.get("last_contact_date")),
                        "phone": lead.get("phone"),
                        "email": lead.get("email"),
                        "interest_level": lead.get("interest_level"),
                        "potential_deal_value": lead.get("potential_deal_value"),
                        "customer_requirements": lead.get("customer_requirements"),
                        "followup_id": fu_followup_id.get(lid),
                        "discussion": fu_discussion.get(lid),
                        "next_action": fu_next_action.get(lid),
                        "outcome_notes": fu_notes.get(lid),
                        "completed_at": latest_completed.isoformat() if isinstance(latest_completed, datetime) else str(latest_completed),
                        "completed_by": fu_completed_by.get(lid),
                        "bucket": "completed",
                    })
            continue  # skip regular queue for completed tasks

        # Determine due date
        explicit_next = _as_date(fu_next.get(lid))
        if explicit_next is not None:
            due = explicit_next
        else:
            last = _as_date(lead.get("last_contact_date"))
            cadence = STAGE_CADENCE.get(canonical, 3)
            due = (last + timedelta(days=cadence)) if last else today

        days_to = (due - today).days

        # Only include in the queue if within our horizon (or overdue)
        if days_to > upcoming_days:
            continue

        # Recommended action from stage + notes override
        action = STAGE_ACTION.get(canonical, "Follow Up")
        reason = f"{canonical} — action required"
        note_text = lead.get("remarks") or lead.get("procurement_remarks") or lead.get("internal_notes") or lead.get("next_action_plan")
        suggestion = suggest_from_note(note_text)
        if suggestion.urgency == "HIGH":
            action = suggestion.action
            reason = suggestion.reason

        task = {
            "lead_id": lid,
            "company_name": lead.get("company_name"),
            "assigned_to": lead.get("assigned_to"),
            "status": lead.get("status"),
            "standard_status": canonical,
            "score": score,
            "band": band,
            "band_emoji": band_emoji(band),
            "lead_category": lead.get("lead_category") or "C",
            "buyer_engagement_frequency": lead.get("buyer_engagement_frequency") or "Medium",
            "recommended_action": action,
            "reason": reason,
            "next_action_plan": (lead.get("next_action_plan") or "")[:120],
            "due_date": due,
            "due_label": ("Overdue" if days_to < 0
                          else "Today" if days_to == 0
                          else "Tomorrow" if days_to == 1
                          else f"In {days_to}d"),
            "days_to": days_to,
            "last_contact_date": _as_date(lead.get("last_contact_date")),
            "phone": lead.get("phone"),
            "email": lead.get("email"),
            "whatsapp_number": lead.get("whatsapp_number"),
            "product_interest": lead.get("product_interest"),
            "country": lead.get("country"),
            "followup_id": fu_followup_id.get(lid),
            "discussion": fu_discussion.get(lid),
            "next_action": fu_next_action.get(lid),
            "outcome_notes": fu_notes.get(lid),
            "completed_at": None,
            "completed_by": fu_completed_by.get(lid),
            "interest_level": lead.get("interest_level"),
            "potential_deal_value": lead.get("potential_deal_value"),
            "customer_requirements": lead.get("customer_requirements"),
            "bucket": ("overdue" if days_to < 0
                       else "today" if days_to == 0
                       else "upcoming"),
        }

        if days_to < 0:
            overdue.append(task)
        elif days_to == 0:
            today_tasks.append(task)
        else:
            upcoming.append(task)

    # Sort each bucket: higher priority_score first
    for bucket in (overdue, today_tasks, upcoming):
        bucket.sort(key=_priority_score, reverse=True)

    actionable = overdue + today_tasks
    actionable.sort(key=_priority_score, reverse=True)
    today_capped = actionable[:max_today]

    summary = {
        "overdue": len(overdue),
        "today": len(today_tasks),
        "actionable_today": len(actionable),
        "upcoming": len(upcoming),
        "capped_shown": len(today_capped),
        "overflow": max(0, len(actionable) - len(today_capped)),
        "hot": sum(1 for t in actionable if t["band"] == "HOT"),
        "warm": sum(1 for t in actionable if t["band"] == "WARM"),
    }

    return {
        "overdue": overdue,
        "today": today_tasks,
        "upcoming": upcoming,
        "actionable_today": actionable,
        "today_capped": today_capped,
        "completed": completed_tasks,
        "summary": summary,
    }
