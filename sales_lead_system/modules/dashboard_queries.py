"""Reusable live dashboard queries backed by MySQL."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

import pandas as pd
from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session

from database.models import ActivityLog, EngagementEvent, FollowUp, Lead
from modules.status_taxonomy import is_open, is_won, to_standard


# Raw stored-status groupings (kept for backward-compatible SQL-level counts).
ACTIVE_STATUSES = (
    "Active", "Prospect", "Nurture", "OutReach", "Requirement Understanding",
    "Quotation Sent", "Samples Sent", "Negotiation", "Follow Up Stage",
    "NEW", "PROSPECT", "NURTURING", "NEGOTIATION", "QUOTATION SENT", "SAMPLE SENT",
)
NURTURE_STATUSES = ("Nurture", "NURTURING", "Nurturing")
CONVERTED_STATUSES = ("Order Closed", "Converted", "CONVERTED")


def _standard_counts(session: Session, user: dict[str, Any]) -> dict[str, int]:
    """Count leads grouped by the canonical standard status (mapping layer)."""
    rows = session.execute(
        select(Lead.status, func.count()).where(lead_scope(user)).group_by(Lead.status)
    ).all()
    counts: dict[str, int] = {}
    for raw_status, n in rows:
        standard = to_standard(raw_status)
        counts[standard] = counts.get(standard, 0) + int(n)
    return counts


def lead_scope(user: dict[str, Any]):
    """Return the standard role-aware lead filter."""
    base = Lead.deleted_at.is_(None)
    if user.get("role") == "Salesperson":
        return and_(base, Lead.assigned_to == user.get("full_name"))
    return base


def get_total_leads(session: Session, user: dict[str, Any]) -> int:
    """Count active, non-deleted leads."""
    return session.scalar(select(func.count()).select_from(Lead).where(lead_scope(user))) or 0


def get_active_leads(session: Session, user: dict[str, Any]) -> int:
    """Count leads still in an open/actionable pipeline state (standard layer)."""
    counts = _standard_counts(session, user)
    return sum(n for status, n in counts.items() if is_open(status))


def get_nurturing_leads(session: Session, user: dict[str, Any]) -> int:
    """Count nurturing leads (standard layer)."""
    return _standard_counts(session, user).get("Nurturing", 0)


def get_converted_leads(session: Session, user: dict[str, Any]) -> int:
    """Count converted leads (standard layer)."""
    counts = _standard_counts(session, user)
    return sum(n for status, n in counts.items() if is_won(status))


def get_overdue_followups(session: Session, user: dict[str, Any]) -> int:
    """Count follow-ups whose next date has passed."""
    today = date.today()
    return (
        session.scalar(
            select(func.count()).select_from(FollowUp).join(Lead).where(lead_scope(user), FollowUp.next_followup < today)
        )
        or 0
    )


def get_due_today_followups(session: Session, user: dict[str, Any]) -> int:
    """Count follow-ups due today."""
    today = date.today()
    return (
        session.scalar(
            select(func.count()).select_from(FollowUp).join(Lead).where(lead_scope(user), FollowUp.next_followup == today)
        )
        or 0
    )


def get_conversion_rate(session: Session, user: dict[str, Any]) -> float:
    """Return conversion rate as a percentage."""
    total = get_total_leads(session, user)
    converted = get_converted_leads(session, user)
    return round(converted / total * 100, 1) if total else 0.0


def get_leads_dataframe(session: Session, user: dict[str, Any], limit: int = 500) -> pd.DataFrame:
    """Return live leads for page tables and charts, with derived standard_status."""
    stmt = select(Lead).where(lead_scope(user)).order_by(Lead.updated_at.desc()).limit(limit)
    df = pd.DataFrame([{column.name: getattr(lead, column.name) for column in Lead.__table__.columns} for lead in session.scalars(stmt)])
    if not df.empty and "status" in df.columns:
        # Non-destructive: keep raw 'status', add canonical 'standard_status'
        df["standard_status"] = df["status"].map(to_standard)
    return df


def get_followups_dataframe(session: Session, user: dict[str, Any], horizon_days: int = 30) -> pd.DataFrame:
    """Return live follow-up rows joined to lead context."""
    max_date = date.today() + timedelta(days=horizon_days)
    stmt = (
        select(FollowUp, Lead)
        .join(Lead)
        .where(lead_scope(user), or_(FollowUp.next_followup.is_(None), FollowUp.next_followup <= max_date))
        .order_by(FollowUp.next_followup.asc())
    )
    rows = []
    for followup, lead in session.execute(stmt):
        rows.append(
            {
                "followup_id": followup.followup_id,
                "lead_id": lead.lead_id,
                "company_name": lead.company_name,
                "status": lead.status,
                "assigned_to": lead.assigned_to,
                "last_contact_date": lead.last_contact_date,
                "followup_date": followup.followup_date,
                "discussion": followup.discussion,
                "next_action": followup.next_action,
                "next_followup": followup.next_followup,
                "updated_by": followup.updated_by,
            }
        )
    return pd.DataFrame(rows)


def get_salesperson_stats(session: Session, user: dict[str, Any]) -> pd.DataFrame:
    """Aggregate live salesperson performance stats."""
    converted = func.sum(case((Lead.status.in_(CONVERTED_STATUSES), 1), else_=0)).label("conversions")
    active = func.sum(case((Lead.status.in_(ACTIVE_STATUSES), 1), else_=0)).label("active_leads")
    stmt = (
        select(
            Lead.assigned_to.label("assigned_to"),
            func.count(Lead.lead_id).label("assigned_leads"),
            active,
            converted,
        )
        .where(lead_scope(user))
        .group_by(Lead.assigned_to)
    )
    df = pd.DataFrame([dict(row._mapping) for row in session.execute(stmt)])
    if df.empty:
        return df
    df["conversion_rate"] = (df["conversions"] / df["assigned_leads"] * 100).round(1)
    overdue = get_followups_dataframe(session, user, horizon_days=365)
    if overdue.empty:
        df["overdue_followups"] = 0
    else:
        overdue = overdue[overdue["next_followup"].notna() & (overdue["next_followup"] < date.today())]
        counts = overdue.groupby("assigned_to").size().to_dict()
        df["overdue_followups"] = df["assigned_to"].map(counts).fillna(0).astype(int)
    return df


def get_engagement_stats(session: Session, user: dict[str, Any], days: int = 7) -> dict[str, Any]:
    """Engagement events in the last N days, scoped by role, grouped by type & user."""
    since = datetime.combine(date.today() - timedelta(days=days), datetime.min.time())
    stmt = select(EngagementEvent).join(Lead, EngagementEvent.lead_id == Lead.lead_id).where(
        lead_scope(user), EngagementEvent.occurred_at >= since
    )
    by_type: dict[str, int] = {}
    by_user: dict[str, int] = {}
    today_done = 0
    start_today = datetime.combine(date.today(), datetime.min.time())
    total = 0
    for ev in session.scalars(stmt):
        total += 1
        by_type[ev.event_type] = by_type.get(ev.event_type, 0) + 1
        if ev.user_name:
            by_user[ev.user_name] = by_user.get(ev.user_name, 0) + 1
        if ev.occurred_at and ev.occurred_at >= start_today:
            today_done += 1
    return {
        "total": total,
        "calls": by_type.get("call", 0),
        "whatsapp": by_type.get("whatsapp", 0),
        "emails": by_type.get("email", 0),
        "meetings": by_type.get("meeting", 0),
        "followups": by_type.get("followup", 0),
        "today_done": today_done,
        "by_user": by_user,
    }


def get_recent_activities(session: Session, limit: int = 12) -> pd.DataFrame:
    """Return recent audit events."""
    stmt = select(ActivityLog).order_by(ActivityLog.timestamp.desc()).limit(limit)
    return pd.DataFrame(
        [
            {
                "timestamp": log.timestamp,
                "action": log.action,
                "user_name": log.user_name,
                "lead_id": log.lead_id,
                "remarks": log.remarks,
            }
            for log in session.scalars(stmt)
        ]
    )
