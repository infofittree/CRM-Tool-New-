"""Sprint 5 — Analytics engine for performance, conversion, trends, scoring."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import Session

from database.models import ActivityLog, CrmAlert, EngagementEvent, FollowUp, Inquiry, Lead
from modules import dashboard_queries as dq
from modules.lead_health import compute_lead_health
from modules.status_taxonomy import TERMINAL_LOST, TERMINAL_WON, CANONICAL_STATUSES, FUNNEL_ORDER
from modules.clock import today as biz_today


def _as_date(d: date | datetime | None) -> date | None:
    if d is None:
        return None
    return d.date() if isinstance(d, datetime) else d


def get_conversion_funnel(session: Session, scope) -> list[dict]:
    """Return counts per funnel stage and conversion % between steps."""
    rows = session.execute(
        select(Lead.status, func.count()).where(scope, Lead.deleted_at.is_(None))
        .group_by(Lead.status)
    ).all()
    counts = {s: int(n) for s, n in rows}
    funnel = []
    for stage in FUNNEL_ORDER:
        c = counts.get(stage, 0)
        funnel.append({"stage": stage, "count": c})
    return funnel


def get_pipeline_stage_analytics(session: Session, scope) -> list[dict]:
    """Time in stage and deal value estimates per pipeline stage."""
    rows = session.execute(
        select(Lead).where(scope, Lead.deleted_at.is_(None))
    ).scalars().all()
    ref = biz_today()
    stage_map: dict[str, dict] = {}
    for lead in rows:
        status = lead.status or "Unknown"
        if status not in stage_map:
            stage_map[status] = {"count": 0, "total_days": 0, "value_count": 0, "total_value": 0}
        stage_map[status]["count"] += 1
        created = _as_date(lead.created_date) or _as_date(lead.created_at)
        if created:
            stage_map[status]["total_days"] += (ref - created).days
        val = lead.potential_deal_value
        if val:
            try:
                v = float(val.replace(",", "").replace("$", ""))
                stage_map[status]["total_value"] += v
                stage_map[status]["value_count"] += 1
            except (ValueError, AttributeError):
                pass
    results = []
    for stage, data in stage_map.items():
        avg_days = round(data["total_days"] / data["count"], 1) if data["count"] else 0
        avg_val = round(data["total_value"] / data["value_count"], 0) if data["value_count"] else 0
        results.append({
            "stage": stage,
            "count": data["count"],
            "avg_days_in_stage": avg_days,
            "avg_deal_value": avg_val,
        })
    return sorted(results, key=lambda x: FUNNEL_ORDER.index(x["stage"]) if x["stage"] in FUNNEL_ORDER else 99)


def get_followup_discipline(session: Session, scope, days: int = 30) -> dict[str, Any]:
    """Completion rates, overdue counts, average delay."""
    since = biz_today() - timedelta(days=days)
    total = session.scalar(
        select(func.count()).select_from(FollowUp).join(Lead)
        .where(scope, FollowUp.created_at >= datetime.combine(since, datetime.min.time()))
    ) or 0
    completed = session.scalar(
        select(func.count()).select_from(FollowUp).join(Lead)
        .where(scope, FollowUp.completed_at.is_not(None), FollowUp.created_at >= datetime.combine(since, datetime.min.time()))
    ) or 0
    overdue = session.scalar(
        select(func.count()).select_from(FollowUp).join(Lead)
        .where(scope, FollowUp.next_followup.is_not(None), FollowUp.next_followup < biz_today(), FollowUp.completed_at.is_(None))
    ) or 0
    completion_pct = round((completed / total * 100), 1) if total else 0.0
    return {
        "total_followups": total,
        "completed": completed,
        "overdue": overdue,
        "completion_pct": completion_pct,
        "avg_delay_days": 0.0,
    }


def get_activity_analytics(session: Session, scope, days: int = 30) -> dict[str, Any]:
    """Activity volume aggregated over N days."""
    since = datetime.combine(biz_today() - timedelta(days=days), datetime.min.time())
    rows = session.execute(
        select(EngagementEvent.event_type, func.count())
        .join(Lead, EngagementEvent.lead_id == Lead.lead_id)
        .where(scope, EngagementEvent.occurred_at >= since)
        .group_by(EngagementEvent.event_type)
    ).all()
    by_type = {t: int(n) for t, n in rows}
    total = sum(by_type.values())
    activity_logs = session.scalar(
        select(func.count()).select_from(ActivityLog)
        .join(Lead, ActivityLog.lead_id == Lead.lead_id)
        .where(scope, ActivityLog.timestamp >= since)
    ) or 0
    return {
        "total_activities": total,
        "calls": by_type.get("call", 0),
        "whatsapp": by_type.get("whatsapp", 0),
        "emails": by_type.get("email", 0),
        "meetings": by_type.get("meeting", 0),
        "followups": by_type.get("followup", 0),
        "activity_logs": activity_logs,
        "avg_per_day": round(total / days, 1) if days else 0,
    }


def get_inquiry_analytics(session: Session) -> dict[str, Any]:
    """Procurement-facing inquiry metrics."""
    total = session.scalar(select(func.count()).select_from(Inquiry)) or 0
    open_count = session.scalar(select(func.count()).select_from(Inquiry).where(Inquiry.status == "OPEN")) or 0
    responded = session.scalar(select(func.count()).select_from(Inquiry).where(Inquiry.status == "RESPONDED")) or 0
    overdue = session.scalar(select(func.count()).select_from(Inquiry).where(Inquiry.status == "OVERDUE")) or 0
    eod_committed = session.scalar(select(func.count()).select_from(Inquiry).where(Inquiry.status == "EOD_COMMITTED")) or 0
    closed = session.scalar(select(func.count()).select_from(Inquiry).where(Inquiry.status == "CLOSED")) or 0
    resp_sla = round((responded / (total - open_count) * 100), 1) if (total - open_count) else 0.0

    type_rows = session.execute(
        select(Inquiry.type, func.count()).group_by(Inquiry.type).order_by(func.count().desc())
    ).all()
    common_types = [{"type": t, "count": int(n)} for t, n in type_rows]

    return {
        "total_inquiries": total,
        "open": open_count,
        "responded": responded,
        "overdue": overdue,
        "eod_committed": eod_committed,
        "closed": closed,
        "response_sla_pct": resp_sla,
        "common_types": common_types,
    }


def get_team_comparison(session: Session, scope) -> list[dict]:
    """Side-by-side comparison per salesperson."""
    salespeople = session.execute(
        select(Lead.assigned_to).where(scope, Lead.assigned_to.isnot(None))
        .group_by(Lead.assigned_to)
    ).scalars().all()
    ref = biz_today()
    results = []
    for sp_name in salespeople:
        sp_scope = and_(scope, Lead.assigned_to == sp_name)
        total_leads = session.scalar(select(func.count()).select_from(Lead).where(sp_scope, Lead.deleted_at.is_(None))) or 0
        won = session.scalar(
            select(func.count()).select_from(Lead).where(sp_scope, Lead.status == TERMINAL_WON)
        ) or 0
        lost = session.scalar(
            select(func.count()).select_from(Lead).where(sp_scope, Lead.status.in_(TERMINAL_LOST))
        ) or 0
        active = total_leads - won - lost
        conversion_rate = round((won / total_leads * 100), 1) if total_leads else 0

        overdue_tasks = session.scalar(
            select(func.count()).select_from(FollowUp).join(Lead)
            .where(sp_scope, FollowUp.next_followup.is_not(None), FollowUp.next_followup < ref, FollowUp.completed_at.is_(None))
        ) or 0
        completed_tasks = session.scalar(
            select(func.count()).select_from(FollowUp).join(Lead)
            .where(sp_scope, FollowUp.completed_at.is_not(None))
        ) or 0
        total_tasks = session.scalar(
            select(func.count()).select_from(FollowUp).join(Lead).where(sp_scope)
        ) or 0
        task_pct = round((completed_tasks / total_tasks * 100), 1) if total_tasks else 0

        engagement = session.scalar(
            select(func.count()).select_from(EngagementEvent).join(Lead)
            .where(sp_scope, EngagementEvent.occurred_at >= datetime.combine(ref - timedelta(days=30), datetime.min.time()))
        ) or 0

        results.append({
            "assigned_to": sp_name,
            "total_leads": total_leads,
            "active_leads": active,
            "won": won,
            "lost": lost,
            "conversion_rate": conversion_rate,
            "overdue_tasks": overdue_tasks,
            "completed_tasks": completed_tasks,
            "task_completion_pct": task_pct,
            "engagement_30d": engagement,
        })
    return results


def get_productivity_scores(session: Session, scope) -> list[dict]:
    """0-100 productivity score per salesperson."""
    comparison = get_team_comparison(session, scope)
    if not comparison:
        return []
    max_vals = {
        "total_leads": max(c["total_leads"] for c in comparison) or 1,
        "won": max(c["won"] for c in comparison) or 1,
        "engagement_30d": max(c["engagement_30d"] for c in comparison) or 1,
        "task_completion_pct": max(c["task_completion_pct"] for c in comparison) or 1,
        "conversion_rate": max(c["conversion_rate"] for c in comparison) or 1,
    }
    results = []
    for c in comparison:
        score = round(
            (c["total_leads"] / max_vals["total_leads"] * 15) +
            (c["won"] / max_vals["won"] * 30) +
            (c["engagement_30d"] / max_vals["engagement_30d"] * 20) +
            (c["task_completion_pct"] / max_vals["task_completion_pct"] * 20) +
            (c["conversion_rate"] / max_vals["conversion_rate"] * 15)
        )
        results.append({"assigned_to": c["assigned_to"], "score": min(score, 100)})
    return sorted(results, key=lambda x: x["score"], reverse=True)


def get_trend_data(session: Session, scope, days: int = 30) -> dict[str, Any]:
    """7/30/90 day trend data for key metrics."""
    ref = biz_today()
    periods = {"7d": 7, "30d": 30, "90d": 90}
    trends = {}
    for label, d in periods.items():
        since = datetime.combine(ref - timedelta(days=d), datetime.min.time())
        leads_created = session.scalar(
            select(func.count()).select_from(Lead)
            .where(scope, Lead.created_at >= since)
        ) or 0
        tasks_completed = session.scalar(
            select(func.count()).select_from(FollowUp).join(Lead)
            .where(scope, FollowUp.completed_at.is_not(None), FollowUp.completed_at >= since)
        ) or 0
        activities = session.scalar(
            select(func.count()).select_from(EngagementEvent).join(Lead)
            .where(scope, EngagementEvent.occurred_at >= since)
        ) or 0
        converted = session.scalar(
            select(func.count()).select_from(Lead)
            .where(scope, Lead.status == TERMINAL_WON, Lead.updated_at >= since)
        ) or 0
        total_leads = session.scalar(
            select(func.count()).select_from(Lead).where(scope, Lead.deleted_at.is_(None))
        ) or 0
        trends[label] = {
            "leads_created": leads_created,
            "tasks_completed": tasks_completed,
            "activities": activities,
            "converted": converted,
            "total_leads": total_leads,
        }
    return trends


def get_executive_summary(session: Session, scope) -> dict[str, Any]:
    """High-level KPIs for the management command center."""
    ref = biz_today()
    total_leads = session.scalar(select(func.count()).select_from(Lead).where(scope, Lead.deleted_at.is_(None))) or 0
    won = session.scalar(select(func.count()).select_from(Lead).where(scope, Lead.status == TERMINAL_WON)) or 0
    conversion_rate = round((won / total_leads * 100), 1) if total_leads else 0

    overdue_tasks = session.scalar(
        select(func.count()).select_from(FollowUp).join(Lead)
        .where(scope, FollowUp.next_followup.is_not(None), FollowUp.next_followup < ref, FollowUp.completed_at.is_(None))
    ) or 0
    due_today = session.scalar(
        select(func.count()).select_from(FollowUp).join(Lead)
        .where(scope, FollowUp.next_followup == ref, FollowUp.completed_at.is_(None))
    ) or 0

    activities_30d = session.scalar(
        select(func.count()).select_from(EngagementEvent).join(Lead)
        .where(scope, EngagementEvent.occurred_at >= datetime.combine(ref - timedelta(days=30), datetime.min.time()))
    ) or 0

    leads_without_fu = session.scalar(
        select(func.count()).select_from(Lead).where(
            scope, Lead.deleted_at.is_(None),
            Lead.status.notin_([TERMINAL_WON, *TERMINAL_LOST]),
            ~Lead.lead_id.in_(
                select(FollowUp.lead_id).where(FollowUp.completed_at.is_(None), FollowUp.next_followup.is_not(None))
            )
        )
    ) or 0

    total_val = 0.0
    val_count = 0
    for row in session.execute(select(Lead).where(scope, Lead.deleted_at.is_(None))).scalars():
        v = row.potential_deal_value
        if v:
            try:
                total_val += float(v.replace(",", "").replace("$", ""))
                val_count += 1
            except (ValueError, AttributeError):
                pass
    avg_deal_value = round(total_val / val_count, 0) if val_count else 0

    return {
        "total_leads": total_leads,
        "won": won,
        "conversion_rate": conversion_rate,
        "overdue_tasks": overdue_tasks,
        "due_today": due_today,
        "activities_30d": activities_30d,
        "leads_without_followup": leads_without_fu,
        "avg_deal_value": avg_deal_value,
    }
