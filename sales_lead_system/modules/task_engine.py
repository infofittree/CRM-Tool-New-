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

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from database.models import EngagementEvent, FollowUp, Lead
from modules.lead_scoring import band_emoji, score_lead
from modules.notes_engine import suggest_from_note
from modules.status_taxonomy import (
    STAGE_ACTION, STAGE_CADENCE, STAGE_PRIORITY,
    is_open, to_canonical,
)
from modules.clock import today as _biz_today

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
        from sqlalchemy import and_
        return and_(base, Lead.assigned_to == user.get("full_name"))
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

    # Next follow-up date per lead = the date on the MOST RECENTLY ENTERED follow-up
    # row (ordered by followup_id), NOT max() — otherwise rescheduling to an earlier
    # date is ignored because an older row had a further-out date.
    fu_next: dict[str, Any] = {}
    for lid, nf in session.execute(
        select(FollowUp.lead_id, FollowUp.next_followup).order_by(FollowUp.followup_id.asc())
    ).all():
        fu_next[lid] = nf  # later (higher id) rows overwrite → latest decision wins
    fu_counts: dict[str, int] = dict(
        session.execute(select(FollowUp.lead_id, func.count()).group_by(FollowUp.lead_id)).all()
    )
    ev_counts: dict[str, int] = dict(
        session.execute(select(EngagementEvent.lead_id, func.count()).group_by(EngagementEvent.lead_id)).all()
    )

    overdue: list[dict] = []
    today_tasks: list[dict] = []
    upcoming: list[dict] = []

    for lead in session.scalars(select(Lead).where(_scope(user))).all():
        canonical = to_canonical(lead.status)
        if not is_open(canonical):
            continue

        lead_dict = {col.name: getattr(lead, col.name) for col in Lead.__table__.columns}
        score, band, _ = score_lead(lead_dict)

        # Determine due date
        explicit_next = _as_date(fu_next.get(lead.lead_id))
        if explicit_next is not None:
            due = explicit_next
        else:
            last = _as_date(lead.last_contact_date)
            cadence = STAGE_CADENCE.get(canonical, 3)
            due = (last + timedelta(days=cadence)) if last else today

        days_to = (due - today).days

        # Only include in the queue if within our horizon (or overdue)
        if days_to > upcoming_days:
            continue

        # Recommended action from stage + notes override
        action = STAGE_ACTION.get(canonical, "Follow Up")
        reason = f"{canonical} — action required"
        note_text = lead.remarks or lead.procurement_remarks or lead.internal_notes or lead.next_action_plan
        suggestion = suggest_from_note(note_text)
        if suggestion.urgency == "HIGH":
            action = suggestion.action
            reason = suggestion.reason

        task = {
            "lead_id": lead.lead_id,
            "company_name": lead.company_name,
            "assigned_to": lead.assigned_to,
            "status": lead.status,
            "standard_status": canonical,
            "score": score,
            "band": band,
            "band_emoji": band_emoji(band),
            "lead_category": lead.lead_category or "C",
            "buyer_engagement_frequency": lead.buyer_engagement_frequency or "Medium",
            "recommended_action": action,
            "reason": reason,
            "next_action_plan": (lead.next_action_plan or "")[:120],
            "due_date": due,
            "due_label": ("Overdue" if days_to < 0
                          else "Today" if days_to == 0
                          else "Tomorrow" if days_to == 1
                          else f"In {days_to}d"),
            "days_to": days_to,
            "last_contact_date": _as_date(lead.last_contact_date),
            "phone": lead.phone,
            "email": lead.email,
            "whatsapp_number": lead.whatsapp_number,
            "product_interest": lead.product_interest,
            "country": lead.country,
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
        "summary": summary,
    }
