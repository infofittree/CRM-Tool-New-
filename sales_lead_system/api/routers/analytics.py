"""Analytics API — performance, conversion, trends, scoring."""

from __future__ import annotations

import csv
import io
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.responses import Response

from api.deps import get_current_user, get_db, require_role
from database.models import Lead, User
from modules import analytics_engine as ae
from modules import dashboard_queries as dq

router = APIRouter(prefix="/analytics")


def _resolve_user(
    current_user: dict,
    salesperson: str | None,
    db: Session,
) -> dict:
    if not salesperson:
        return current_user
    role = current_user.get("role", "")
    if role in ("Salesperson", "salesperson"):
        return current_user
    user = db.scalar(
        select(User).where(
            User.full_name == salesperson,
            User.is_active.is_(True),
            User.deleted_at.is_(None),
        )
    )
    if not user:
        raise HTTPException(status_code=404, detail=f"User '{salesperson}' not found")
    return {"username": user.username, "full_name": user.full_name, "role": user.role}


@router.get("/executive-summary")
def executive_summary(
    salesperson: str | None = Query(None),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    target = _resolve_user(current_user, salesperson, db)
    scope = dq.lead_scope(target)
    return ae.get_executive_summary(db, scope)


@router.get("/conversion-funnel")
def conversion_funnel(
    salesperson: str | None = Query(None),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    target = _resolve_user(current_user, salesperson, db)
    scope = dq.lead_scope(target)
    return ae.get_conversion_funnel(db, scope)


@router.get("/pipeline-stages")
def pipeline_stages(
    salesperson: str | None = Query(None),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    target = _resolve_user(current_user, salesperson, db)
    scope = dq.lead_scope(target)
    return ae.get_pipeline_stage_analytics(db, scope)


@router.get("/followup-discipline")
def followup_discipline(
    days: int = Query(30, ge=1, le=365),
    salesperson: str | None = Query(None),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    target = _resolve_user(current_user, salesperson, db)
    scope = dq.lead_scope(target)
    return ae.get_followup_discipline(db, scope, days=days)


@router.get("/activity-analytics")
def activity_analytics(
    days: int = Query(30, ge=1, le=365),
    salesperson: str | None = Query(None),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    target = _resolve_user(current_user, salesperson, db)
    scope = dq.lead_scope(target)
    return ae.get_activity_analytics(db, scope, days=days)


@router.get("/inquiry")
def inquiry_analytics(
    current_user: dict = Depends(require_role(["Admin", "Manager", "Procurement", "procurement_head"])),
    db: Session = Depends(get_db),
):
    return ae.get_inquiry_analytics(db)


@router.get("/trends")
def trends(
    days: int = Query(30, ge=7, le=365),
    salesperson: str | None = Query(None),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    target = _resolve_user(current_user, salesperson, db)
    scope = dq.lead_scope(target)
    return ae.get_trend_data(db, scope, days=days)


@router.get("/productivity")
def productivity(
    salesperson: str | None = Query(None),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    target = _resolve_user(current_user, salesperson, db)
    scope = dq.lead_scope(target)
    return ae.get_productivity_scores(db, scope)


@router.get("/team-comparison")
def team_comparison(
    salesperson: str | None = Query(None),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    target = _resolve_user(current_user, salesperson, db)
    scope = dq.lead_scope(target)
    return ae.get_team_comparison(db, scope)


@router.get("/salesperson/{name}")
def salesperson_analytics(
    name: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    role = current_user.get("role", "")
    if role in ("Salesperson", "salesperson"):
        name = current_user.get("full_name", name)
    sp_scope = Lead.assigned_to == name
    kpi = ae.get_executive_summary(db, sp_scope)
    funnel = ae.get_conversion_funnel(db, sp_scope)
    pipeline = ae.get_pipeline_stage_analytics(db, sp_scope)
    fu = ae.get_followup_discipline(db, sp_scope)
    act = ae.get_activity_analytics(db, sp_scope)
    prod = [s for s in ae.get_productivity_scores(db, sp_scope) if s["assigned_to"] == name]
    return {
        "kpi": kpi,
        "conversion_funnel": funnel,
        "pipeline_stages": pipeline,
        "followup_discipline": fu,
        "activity_analytics": act,
        "productivity_score": prod[0]["score"] if prod else 0,
    }


@router.get("/export")
def export_analytics(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    salesperson: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    target = _resolve_user(current_user, salesperson, db)
    rows = db.execute(select(Lead).where(dq.lead_scope(target))).scalars().all()
    output = io.StringIO()
    w = csv.writer(output)
    w.writerow([
        "lead_id", "company", "contact", "status", "assigned_to", "created_date",
        "interest_level", "potential_deal_value", "customer_requirements",
        "last_contact_date", "has_pending_followup",
    ])
    for r in rows:
        w.writerow([
            r.lead_id, r.company_name, r.contact_person, r.status,
            r.assigned_to, str(r.created_date or ""),
            r.interest_level or "", r.potential_deal_value or "",
            r.customer_requirements or "", str(r.last_contact_date or ""),
            r.has_pending_followup or False,
        ])
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=analytics_export.csv"},
    )
