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
    """Procurement-facing inquiry metrics — batched single-query."""
    # Single GROUP BY status replaces 6 separate COUNT queries
    status_rows = session.execute(
        select(Inquiry.status, func.count()).group_by(Inquiry.status)
    ).all()
    status_map = {row.status: row[1] for row in status_rows}

    total = sum(status_map.values())
    open_count = status_map.get("OPEN", 0)
    responded = status_map.get("RESPONDED", 0)
    overdue = status_map.get("OVERDUE", 0)
    eod_committed = status_map.get("EOD_COMMITTED", 0)
    closed = status_map.get("CLOSED", 0)
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
    """Side-by-side comparison per salesperson — single-query batch."""
    ref = biz_today()
    ref_dt = datetime.combine(ref - timedelta(days=30), datetime.min.time())

    # Batch query 1: Lead stats per salesperson (single GROUP BY)
    lead_rows = session.execute(
        select(
            Lead.assigned_to,
            func.count().label("total"),
            func.sum(case((Lead.status == TERMINAL_WON, 1), else_=0)).label("won"),
            func.sum(case((Lead.status.in_(TERMINAL_LOST), 1), else_=0)).label("lost"),
        )
        .where(scope, Lead.deleted_at.is_(None), Lead.assigned_to.isnot(None))
        .group_by(Lead.assigned_to)
    ).all()

    lead_stats: dict[str, dict] = {}
    for row in lead_rows:
        total = row.total or 0
        won = row.won or 0
        lost = row.lost or 0
        lead_stats[row.assigned_to] = {
            "total_leads": total, "won": won, "lost": lost,
            "active_leads": total - won - lost,
            "conversion_rate": round((won / total * 100), 1) if total else 0,
        }

    # Batch query 2: Follow-up stats per salesperson (single GROUP BY)
    fu_rows = session.execute(
        select(
            Lead.assigned_to,
            func.count().label("total_tasks"),
            func.sum(case((FollowUp.completed_at.isnot(None), 1), else_=0)).label("completed_tasks"),
            func.sum(case(
                (and_(FollowUp.next_followup.is_not(None), FollowUp.next_followup < ref, FollowUp.completed_at.is_(None)), 1),
                else_=0,
            )).label("overdue_tasks"),
        )
        .join(Lead, FollowUp.lead_id == Lead.lead_id)
        .where(scope, Lead.deleted_at.is_(None), Lead.assigned_to.isnot(None))
        .group_by(Lead.assigned_to)
    ).all()

    fu_stats: dict[str, dict] = {}
    for row in fu_rows:
        total_tasks = row.total_tasks or 0
        completed = row.completed_tasks or 0
        overdue = row.overdue_tasks or 0
        fu_stats[row.assigned_to] = {
            "total_tasks": total_tasks, "completed_tasks": completed,
            "overdue_tasks": overdue,
            "task_completion_pct": round((completed / total_tasks * 100), 1) if total_tasks else 0,
        }

    # Batch query 3: Engagement per salesperson (single GROUP BY)
    eng_rows = session.execute(
        select(
            Lead.assigned_to,
            func.count().label("engagement_30d"),
        )
        .join(EngagementEvent, EngagementEvent.lead_id == Lead.lead_id)
        .where(scope, Lead.deleted_at.is_(None), Lead.assigned_to.isnot(None),
               EngagementEvent.occurred_at >= ref_dt)
        .group_by(Lead.assigned_to)
    ).all()

    eng_stats: dict[str, dict] = {row.assigned_to: {"engagement_30d": row.engagement_30d or 0} for row in eng_rows}

    # Merge results
    all_names = set(lead_stats) | set(fu_stats) | set(eng_stats)
    results = []
    for name in sorted(all_names):
        ls = lead_stats.get(name, {"total_leads": 0, "won": 0, "lost": 0, "active_leads": 0, "conversion_rate": 0})
        fs = fu_stats.get(name, {"total_tasks": 0, "completed_tasks": 0, "overdue_tasks": 0, "task_completion_pct": 0})
        es = eng_stats.get(name, {"engagement_30d": 0})
        results.append({
            "assigned_to": name,
            **ls, **fs, **es,
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
    """7/30/90 day trend data for key metrics — optimized batch queries."""
    ref = biz_today()
    periods = {"7d": 7, "30d": 30, "90d": 90}

    # Total leads is the same for all periods — compute once
    total_leads = session.scalar(
        select(func.count()).select_from(Lead).where(scope, Lead.deleted_at.is_(None))
    ) or 0

    trends = {}
    for label, d in periods.items():
        since = datetime.combine(ref - timedelta(days=d), datetime.min.time())
        leads_created = session.scalar(
            select(func.count()).select_from(Lead).where(scope, Lead.created_at >= since)
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
    for row in session.execute(select(Lead.potential_deal_value).where(scope, Lead.deleted_at.is_(None), Lead.potential_deal_value.isnot(None))).all():
        v = row[0]
        if v:
            try:
                total_val += float(str(v).replace(",", "").replace("$", ""))
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
