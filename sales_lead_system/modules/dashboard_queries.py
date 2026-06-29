"""Reusable live dashboard queries backed by MySQL."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

import pandas as pd
from sqlalchemy import and_, case, func, or_, select


from sqlalchemy.orm import Session

from database.models import ActivityLog, EngagementEvent, FollowUp, Lead
from modules.status_taxonomy import CANONICAL_STATUSES, is_open, is_won, to_standard
from modules.clock import today as biz_today


# ── Column name cache (avoids repeated SQLAlchemy reflection) ─────────────────
_LEAD_COLUMN_NAMES: list[str] | None = None

def _lead_columns() -> list[str]:
    global _LEAD_COLUMN_NAMES
    if _LEAD_COLUMN_NAMES is None:
        _LEAD_COLUMN_NAMES = [c.name for c in Lead.__table__.columns]
    return _LEAD_COLUMN_NAMES


# Canonical status groupings (backward-compat aliases; DB now stores canonical values).
ACTIVE_STATUSES = tuple(s for s in CANONICAL_STATUSES if s not in ("Lost", "Order Closed"))
NURTURE_STATUSES = ("Nurturing",)
CONVERTED_STATUSES = ("Order Closed",)


def lead_scope(user: dict[str, Any]):
    """Return the standard role-aware lead filter.

    Salesperson sees only their assigned leads; match is case-insensitive.
    Admin and Manager see all non-deleted leads.
    """
    base = Lead.deleted_at.is_(None)
    if user.get("role") == "Salesperson":
        name = (user.get("full_name") or "").strip()
        return and_(base, Lead.assigned_to.isnot(None), func.lower(Lead.assigned_to) == name.lower())
    return base


def get_status_counts(session: Session, users: list[dict[str, Any]] | None = None, user: dict[str, Any] | None = None) -> dict[str, int]:
    """Return counts per canonical status — single GROUP BY query.

    Accept either a list of users (for multi-user dashboard) or a single user.
    """
    if users is not None:
        scopes = [lead_scope(u) for u in users]
        where_clause = and_(*scopes) if scopes else Lead.deleted_at.is_(None)
    elif user is not None:
        where_clause = lead_scope(user)
    else:
        where_clause = Lead.deleted_at.is_(None)

    rows = session.execute(
        select(Lead.status, func.count()).where(where_clause).group_by(Lead.status)
    ).all()
    counts: dict[str, int] = {}
    for raw_status, n in rows:
        standard = to_standard(raw_status)
        counts[standard] = counts.get(standard, 0) + int(n)
    return counts


def get_total_leads(session: Session, user: dict[str, Any]) -> int:
    """Count active, non-deleted leads."""
    return session.scalar(select(func.count()).select_from(Lead).where(lead_scope(user))) or 0


def get_active_leads(session: Session, user: dict[str, Any], counts: dict[str, int] | None = None) -> int:
    """Count leads still in an open/actionable pipeline state (standard layer).

    Accepts optional pre-computed *counts* to avoid redundant queries.
    """
    if counts is None:
        counts = get_status_counts(session, user=user)
    return sum(n for status, n in counts.items() if is_open(status))


def get_nurturing_leads(session: Session, user: dict[str, Any], counts: dict[str, int] | None = None) -> int:
    """Count nurturing leads (standard layer).

    Accepts optional pre-computed *counts* to avoid redundant queries.
    """
    if counts is None:
        counts = get_status_counts(session, user=user)
    return counts.get("Nurturing", 0)


def get_converted_leads(session: Session, user: dict[str, Any], counts: dict[str, int] | None = None) -> int:
    """Count converted leads (standard layer).

    Accepts optional pre-computed *counts* to avoid redundant queries.
    """
    if counts is None:
        counts = get_status_counts(session, user=user)
    return sum(n for status, n in counts.items() if is_won(status))


def _latest_followup_per_lead(session: Session, user: dict[str, Any]) -> dict[str, Any]:
    """Map lead_id -> next_followup using SQL MAX(followup_id) per lead (single query, no Python iteration)."""
    latest = func.max(FollowUp.followup_id)
    subq = (
        select(FollowUp.lead_id, func.max(FollowUp.followup_id).label("max_id"))
        .join(Lead).where(lead_scope(user))
        .group_by(FollowUp.lead_id)
    ).subquery()
    rows = session.execute(
        select(FollowUp.lead_id, FollowUp.next_followup)
        .join(subq, and_(FollowUp.lead_id == subq.c.lead_id, FollowUp.followup_id == subq.c.max_id))
    ).all()
    return {lid: nf for lid, nf in rows if nf}


def get_overdue_followups(session: Session, user: dict[str, Any]) -> int:
    """Count LEADS whose latest follow-up date has passed using SQL-only count."""
    today = biz_today()
    latest = func.max(FollowUp.followup_id)
    subq = (
        select(FollowUp.lead_id, func.max(FollowUp.followup_id).label("max_id"))
        .join(Lead).where(lead_scope(user))
        .group_by(FollowUp.lead_id)
    ).subquery()
    return session.scalar(
        select(func.count())
        .select_from(FollowUp)
        .join(subq, and_(FollowUp.lead_id == subq.c.lead_id, FollowUp.followup_id == subq.c.max_id))
        .where(FollowUp.next_followup.is_not(None), FollowUp.next_followup < today)
    ) or 0


def get_due_today_followups(session: Session, user: dict[str, Any]) -> int:
    """Count LEADS whose latest follow-up is due today using SQL-only count."""
    today = biz_today()
    latest = func.max(FollowUp.followup_id)
    subq = (
        select(FollowUp.lead_id, func.max(FollowUp.followup_id).label("max_id"))
        .join(Lead).where(lead_scope(user))
        .group_by(FollowUp.lead_id)
    ).subquery()
    return session.scalar(
        select(func.count())
        .select_from(FollowUp)
        .join(subq, and_(FollowUp.lead_id == subq.c.lead_id, FollowUp.followup_id == subq.c.max_id))
        .where(FollowUp.next_followup == today)
    ) or 0


def get_dashboard_counts(session: Session, user: dict[str, Any]) -> dict[str, Any]:
    """Return all dashboard metric counts in a single batch (4 queries, not 10+).

    Call this once on dashboard load and destructure the result.
    """
    scope = lead_scope(user)
    total = session.scalar(select(func.count()).select_from(Lead).where(scope)) or 0
    status_counts = get_status_counts(session, user=user)
    today = biz_today()
    latest = func.max(FollowUp.followup_id)
    subq = (
        select(FollowUp.lead_id, func.max(FollowUp.followup_id).label("max_id"))
        .join(Lead).where(scope)
        .group_by(FollowUp.lead_id)
    ).subquery()
    overdue = session.scalar(
        select(func.count()).select_from(FollowUp)
        .join(subq, and_(FollowUp.lead_id == subq.c.lead_id, FollowUp.followup_id == subq.c.max_id))
        .where(FollowUp.next_followup.is_not(None), FollowUp.next_followup < today)
    ) or 0
    due_today = session.scalar(
        select(func.count()).select_from(FollowUp)
        .join(subq, and_(FollowUp.lead_id == subq.c.lead_id, FollowUp.followup_id == subq.c.max_id))
        .where(FollowUp.next_followup == today)
    ) or 0
    active = sum(n for s, n in status_counts.items() if is_open(s))
    nurturing = status_counts.get("Nurturing", 0)
    converted = sum(n for s, n in status_counts.items() if is_won(s))
    conversion_rate = round(converted / total * 100, 1) if total else 0.0
    return {
        "total": total, "active": active, "nurturing": nurturing,
        "converted": converted, "conversion_rate": conversion_rate,
        "overdue_followups": overdue, "due_today_followups": due_today,
    }


def get_conversion_rate(session: Session, user: dict[str, Any], counts: dict[str, int] | None = None) -> float:
    """Return conversion rate as a percentage.

    Accepts optional pre-computed *counts* to avoid redundant queries.
    """
    if counts is not None:
        converted = sum(n for s, n in counts.items() if is_won(s))
        total = sum(counts.values())
    else:
        total = get_total_leads(session, user)
        converted = get_converted_leads(session, user)
    return round(converted / total * 100, 1) if total else 0.0


def get_leads_dataframe(session: Session, user: dict[str, Any], limit: int = 500) -> pd.DataFrame:
    """Return live leads for page tables and charts, with derived standard_status."""
    from sqlalchemy import select as sa_select
    table = Lead.__table__
    stmt = sa_select(table).where(lead_scope(user)).order_by(table.c.updated_at.desc()).limit(limit)
    rows = session.execute(stmt).all()
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame([dict(r._mapping) for r in rows])
    if "status" in df.columns:
        df["standard_status"] = df["status"].map(to_standard)
    return df


def get_followups_dataframe(session: Session, user: dict[str, Any], horizon_days: int = 30) -> pd.DataFrame:
    """Return live follow-up rows joined to lead context."""
    max_date = biz_today() + timedelta(days=horizon_days)
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
    """Aggregate live salesperson performance stats — overdue counts via SQL subquery."""
    converted = func.sum(case((Lead.status.in_(CONVERTED_STATUSES), 1), else_=0)).label("conversions")
    active = func.sum(case((Lead.status.in_(ACTIVE_STATUSES), 1), else_=0)).label("active_leads")
    stmt = (
        select(
            Lead.assigned_to.label("assigned_to"),
            func.count(Lead.lead_id).label("assigned_leads"),
            active,
            converted,
        )
        .where(lead_scope(user), Lead.assigned_to.isnot(None))
        .group_by(Lead.assigned_to)
    )
    df = pd.DataFrame([dict(row._mapping) for row in session.execute(stmt)])
    if df.empty:
        return df
    df["conversion_rate"] = (df["conversions"] / df["assigned_leads"] * 100).round(1)

    # Overdue followups per salesperson via SQL (no DataFrame load)
    today = biz_today()
    latest = func.max(FollowUp.followup_id)
    subq = (
        select(FollowUp.lead_id, func.max(FollowUp.followup_id).label("max_id"))
        .join(Lead).where(lead_scope(user))
        .group_by(FollowUp.lead_id)
    ).subquery()
    overdue_rows = session.execute(
        select(Lead.assigned_to, func.count())
        .join(FollowUp, FollowUp.lead_id == Lead.lead_id)
        .join(subq, and_(FollowUp.lead_id == subq.c.lead_id, FollowUp.followup_id == subq.c.max_id))
        .where(FollowUp.next_followup.is_not(None), FollowUp.next_followup < today)
        .group_by(Lead.assigned_to)
    ).all()
    overdue_map = {assigned_to: int(n) for assigned_to, n in overdue_rows}
    df["overdue_followups"] = df["assigned_to"].map(overdue_map).fillna(0).astype(int)
    return df


def get_engagement_stats(session: Session, user: dict[str, Any], days: int = 7) -> dict[str, Any]:
    """Engagement events in the last N days — uses SQL GROUP BY, no Python iteration over rows."""
    since = datetime.combine(biz_today() - timedelta(days=days), datetime.min.time())
    start_today = datetime.combine(biz_today(), datetime.min.time())

    # Type breakdown in one query
    type_rows = session.execute(
        select(EngagementEvent.event_type, func.count())
        .join(Lead, EngagementEvent.lead_id == Lead.lead_id)
        .where(lead_scope(user), EngagementEvent.occurred_at >= since)
        .group_by(EngagementEvent.event_type)
    ).all()
    by_type: dict[str, int] = {t: int(n) for t, n in type_rows}
    total = sum(by_type.values())

    # Today's count
    today_count = session.scalar(
        select(func.count())
        .select_from(EngagementEvent)
        .join(Lead, EngagementEvent.lead_id == Lead.lead_id)
        .where(lead_scope(user), EngagementEvent.occurred_at >= start_today)
    ) or 0

    # Per-user breakdown
    user_rows = session.execute(
        select(EngagementEvent.user_name, func.count())
        .join(Lead, EngagementEvent.lead_id == Lead.lead_id)
        .where(lead_scope(user), EngagementEvent.occurred_at >= since, EngagementEvent.user_name.is_not(None))
        .group_by(EngagementEvent.user_name)
    ).all()
    by_user: dict[str, int] = {u: int(n) for u, n in user_rows}

    return {
        "total": total,
        "calls": by_type.get("call", 0),
        "whatsapp": by_type.get("whatsapp", 0),
        "emails": by_type.get("email", 0),
        "meetings": by_type.get("meeting", 0),
        "followups": by_type.get("followup", 0),
        "today_done": today_count,
        "by_user": by_user,
    }


def get_recent_activities(session: Session, limit: int = 12, user: dict[str, Any] | None = None) -> pd.DataFrame:
    """Return recent audit events, optionally filtered by user."""
    stmt = select(ActivityLog).order_by(ActivityLog.timestamp.desc()).limit(limit)
    if user:
        name = (user.get("full_name") or "").strip()
        stmt = select(ActivityLog).where(
            func.lower(ActivityLog.user_name) == name.lower()
        ).order_by(ActivityLog.timestamp.desc()).limit(limit)
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
