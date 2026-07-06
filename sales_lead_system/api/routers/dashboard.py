"""Dashboard router — metrics, charts, activity, health, alerts."""

from __future__ import annotations

import math
from datetime import date, timedelta
from typing import Any

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, and_, case, or_
from sqlalchemy.orm import Session

from api.deps import get_current_user, get_db
from api.schemas import AlertResponse, DashboardCounts, EngagementStats, LeadHealthResponse, PipelineHealthResponse, SalespersonKpi, TodayPrioritiesResponse
from database.models import ActivityLog, CrmAlert, FollowUp, Lead, User
from modules import dashboard_queries as dq
from modules.lead_health import compute_lead_health, compute_pipeline_health, get_health_warnings, get_risk_level
from modules.status_taxonomy import is_open
from modules.clock import today as biz_today

router = APIRouter()


def _clean(records: list[dict]) -> list[dict]:
    """Replace NaN/inf with None and convert non-native types."""
    cleaned: list[dict] = []
    for rec in records:
        clean: dict[str, Any] = {}
        for k, v in rec.items():
            if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                clean[k] = None
            elif isinstance(v, pd.Timestamp):
                clean[k] = v.isoformat()
            else:
                clean[k] = v
        cleaned.append(clean)
    return cleaned


def _resolve_salesperson_user(
    current_user: dict,
    salesperson: str | None,
    db: Session,
) -> dict[str, Any]:
    """Return a synthetic user dict scoped to the given *salesperson*.

    - No *salesperson* → returns current_user (no filtering).
    - Admin/Manager can specify any active user by full_name.
    - Salesperson can only see their own data (ignores param).
    """
    if not salesperson:
        return current_user

    role = current_user.get("role", "")
    if role == "Salesperson":
        return current_user  # already scoped

    user = db.scalar(
        select(User).where(
            User.full_name == salesperson,
            User.is_active.is_(True),
            User.deleted_at.is_(None),
        )
    )
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User '{salesperson}' not found")
    return {"username": user.username, "full_name": user.full_name, "role": user.role}


@router.get("/counts", response_model=DashboardCounts)
def dashboard_counts(
    salesperson: str | None = Query(None, description="Filter by salesperson full_name"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    target = _resolve_salesperson_user(current_user, salesperson, db)
    return DashboardCounts(**dq.get_dashboard_counts(db, target))


@router.get("/leads")
def dashboard_leads(
    limit: int = Query(500, ge=1, le=10000),
    salesperson: str | None = Query(None, description="Filter by salesperson full_name"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    target = _resolve_salesperson_user(current_user, salesperson, db)
    df = dq.get_leads_dataframe(db, target, limit=limit)
    return {"items": _clean(df.to_dict(orient="records")) if not df.empty else []}


@router.get("/followups")
def dashboard_followups(
    horizon_days: int = Query(30, ge=1, le=365),
    salesperson: str | None = Query(None, description="Filter by salesperson full_name"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    target = _resolve_salesperson_user(current_user, salesperson, db)
    df = dq.get_followups_dataframe(db, target, horizon_days=horizon_days)
    return {"items": _clean(df.to_dict(orient="records")) if not df.empty else []}


@router.get("/engagement", response_model=EngagementStats)
def engagement_stats(
    days: int = Query(7, ge=1, le=90),
    salesperson: str | None = Query(None, description="Filter by salesperson full_name"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    target = _resolve_salesperson_user(current_user, salesperson, db)
    return EngagementStats(**dq.get_engagement_stats(db, target, days=days))


@router.get("/salesperson-stats")
def salesperson_stats(
    salesperson: str | None = Query(None, description="Filter to a single salesperson"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    target = _resolve_salesperson_user(current_user, salesperson, db)
    df = dq.get_salesperson_stats(db, target)
    return {"items": _clean(df.to_dict(orient="records")) if not df.empty else []}


@router.get("/activities")
def recent_activities(
    limit: int = Query(12, ge=1, le=100),
    salesperson: str | None = Query(None, description="Filter by salesperson full_name"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    target = _resolve_salesperson_user(current_user, salesperson, db)
    df = dq.get_recent_activities(db, limit=limit, user=target)
    return {"items": _clean(df.to_dict(orient="records")) if not df.empty else []}


# ── Sprint 4 — Pipeline Health ───────────────────────────────────────────────

@router.get("/pipeline-health", response_model=PipelineHealthResponse)
def pipeline_health(
    salesperson: str | None = Query(None),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    target = _resolve_salesperson_user(current_user, salesperson, db)
    scope = dq.lead_scope(target)
    ref = biz_today()

    lead_rows = db.execute(
        select(Lead).where(scope, Lead.deleted_at.is_(None)).order_by(Lead.updated_at.desc()).limit(2000)
    ).scalars().all()

    followups_map: dict[str, list[FollowUp]] = {}
    for lead in lead_rows:
        followups_map[lead.lead_id] = lead.followups or []

    counts = {"healthy": 0, "attention_needed": 0, "at_risk": 0, "stalled": 0}
    for lead in lead_rows:
        health = compute_lead_health(lead, followups_map.get(lead.lead_id), ref)
        if health in counts:
            counts[health] += 1

    return PipelineHealthResponse(**counts, total=len(lead_rows))


# ── Sprint 4 — Today's Priorities ────────────────────────────────────────────

@router.get("/today-priorities", response_model=TodayPrioritiesResponse)
def today_priorities(
    salesperson: str | None = Query(None),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    target = _resolve_salesperson_user(current_user, salesperson, db)
    scope = dq.lead_scope(target)
    ref = biz_today()

    overdue_tasks = db.scalar(
        select(func.count()).select_from(FollowUp).join(Lead, FollowUp.lead_id == Lead.lead_id)
        .where(scope, FollowUp.next_followup.is_not(None), FollowUp.next_followup < ref, FollowUp.completed_at.is_(None))
    ) or 0

    due_today = db.scalar(
        select(func.count()).select_from(FollowUp).join(Lead, FollowUp.lead_id == Lead.lead_id)
        .where(scope, FollowUp.next_followup == ref, FollowUp.completed_at.is_(None))
    ) or 0

    leads_without_followup = db.scalar(
        select(func.count()).select_from(Lead).where(
            scope, Lead.deleted_at.is_(None),
            Lead.status.notin_(["Order Closed", "Lost"]),
            ~Lead.lead_id.in_(
                select(FollowUp.lead_id).where(
                    FollowUp.completed_at.is_(None), FollowUp.next_followup.is_not(None)
                )
            )
        )
    ) or 0

    pipeline = pipeline_health(salesperson, current_user, db)
    return TodayPrioritiesResponse(
        overdue_tasks=overdue_tasks,
        due_today=due_today,
        at_risk_leads=pipeline.at_risk,
        stalled_leads=pipeline.stalled,
        leads_without_followup=leads_without_followup,
    )


# ── Sprint 4 — Salesperson KPIs ──────────────────────────────────────────────

@router.get("/salesperson-kpi")
def salesperson_kpi(
    salesperson: str | None = Query(None),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    target = _resolve_salesperson_user(current_user, salesperson, db)
    scope = dq.lead_scope(target)
    ref = biz_today()

    salespeople = db.execute(
        select(Lead.assigned_to).where(scope, Lead.assigned_to.isnot(None))
        .group_by(Lead.assigned_to).order_by(Lead.assigned_to)
    ).scalars().all()

    results: list[dict] = []
    for sp_name in salespeople:
        sp_scope = and_(scope, Lead.assigned_to == sp_name)

        tasks_due_today = db.scalar(
            select(func.count()).select_from(FollowUp).join(Lead)
            .where(sp_scope, FollowUp.next_followup == ref, FollowUp.completed_at.is_(None))
        ) or 0

        overdue_tasks = db.scalar(
            select(func.count()).select_from(FollowUp).join(Lead)
            .where(sp_scope, FollowUp.next_followup.is_not(None), FollowUp.next_followup < ref, FollowUp.completed_at.is_(None))
        ) or 0

        upcoming_tasks = db.scalar(
            select(func.count()).select_from(FollowUp).join(Lead)
            .where(sp_scope, FollowUp.next_followup > ref, FollowUp.completed_at.is_(None))
        ) or 0

        completed_tasks = db.scalar(
            select(func.count()).select_from(FollowUp).join(Lead)
            .where(sp_scope, FollowUp.completed_at.is_not(None), FollowUp.completed_at >= ref - timedelta(days=7))
        ) or 0

        total = tasks_due_today + overdue_tasks + upcoming_tasks
        overdue_pct = round((overdue_tasks / total * 100), 1) if total else 0.0
        completed_total = completed_tasks + total
        completion_pct = round((completed_tasks / completed_total * 100), 1) if completed_total else 0.0

        results.append({
            "assigned_to": sp_name,
            "tasks_due_today": tasks_due_today,
            "overdue_tasks": overdue_tasks,
            "upcoming_tasks": upcoming_tasks,
            "completed_tasks": completed_tasks,
            "overdue_pct": overdue_pct,
            "completion_pct": completion_pct,
            "avg_delay_days": 0.0,
        })

    return {"items": _clean(results)}


# ── Sprint 4 — Alerts ────────────────────────────────────────────────────────

@router.get("/alerts")
def dashboard_alerts(
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from api.deps import require_role
    from sqlalchemy import or_

    query = select(CrmAlert).order_by(CrmAlert.created_at.desc()).limit(limit)
    if current_user.get("role") == "Salesperson":
        name = (current_user.get("full_name") or "").strip()
        query = query.where(
            or_(CrmAlert.lead_id.is_(None), CrmAlert.lead_id.in_(
                select(Lead.lead_id).where(
                    Lead.assigned_to.isnot(None),
                    func.lower(Lead.assigned_to) == name.lower(),
                    Lead.deleted_at.is_(None),
                )
            ))
        )
    alerts = db.scalars(query).all()
    return {"items": [AlertResponse.model_validate(a) for a in alerts]}


@router.patch("/alerts/{alert_id}/read")
def mark_alert_read(
    alert_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    alert = db.get(CrmAlert, alert_id)
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    alert.is_read = True
    db.commit()
    return {"ok": True}


# ── Sprint 4 — Lead Health ──────────────────────────────────────────────────

@router.get("/lead-health/{lead_id}", response_model=LeadHealthResponse)
def lead_health(
    lead_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    followups = lead.followups or []
    ref = biz_today()
    health = compute_lead_health(lead, followups, ref)
    warnings = get_health_warnings(lead, followups, ref)

    last_contact_days = None
    if lead.last_contact_date:
        last_contact_days = (ref - lead.last_contact_date).days

    next_fu_date = None
    for fu in sorted(followups, key=lambda x: x.next_followup or ref, reverse=False):
        if fu.next_followup and fu.next_followup >= ref and not fu.completed_at:
            next_fu_date = fu.next_followup
            break

    return LeadHealthResponse(
        health=health,
        risk_level=get_risk_level(health),
        warnings=warnings,
        last_activity_days=last_contact_days,
        next_followup_date=next_fu_date,
    )
