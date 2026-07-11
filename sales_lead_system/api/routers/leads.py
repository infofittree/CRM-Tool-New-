"""Leads router — CRUD and operations."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from api.deps import get_current_user, get_db, require_role
from api.schemas import (
    DuplicateCheckResult, FollowUpResponse,
    LeadCreate, LeadResponse, LeadTransfer, LeadUpdate,
    NoteRequest, PaginatedResponse, QuickFollowup, RescheduleRequest,
)
from database.crud import LeadCRUD
from database.models import Lead
from modules.crm_service import CRMService

router = APIRouter()

_EDITABLE_FIELDS = frozenset({
    "contact_person", "phone", "alternate_number", "whatsapp_number",
    "email", "country", "continent", "industry", "website", "city",
    "designation", "lead_source", "product_interest", "assigned_to",
    "priority_level", "remarks", "internal_notes", "procurement_remarks",
    "status", "next_action_plan",
})


@router.get("")
def list_leads(
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=1000),
    search: str | None = Query(None),
    status: str | None = Query(None),
    assigned_to: str | None = Query(None),
    country: str | None = Query(None),
    priority_level: str | None = Query(None),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    scope = _lead_scope_filter(current_user)
    filters = [Lead.deleted_at.is_(None), scope] if scope is not None else [Lead.deleted_at.is_(None)]
    if status:
        filters.append(Lead.status == status)
    if assigned_to:
        from sqlalchemy import func
        filters.append(func.lower(Lead.assigned_to) == assigned_to.lower())
    if country:
        filters.append(Lead.country == country)
    if priority_level:
        filters.append(Lead.priority_level == priority_level)
    if search:
        pattern = f"%{search}%"
        from sqlalchemy import or_
        filters.append(or_(
            Lead.company_name.ilike(pattern),
            Lead.contact_person.ilike(pattern),
            Lead.email.ilike(pattern),
            Lead.phone.ilike(pattern),
        ))
    from sqlalchemy import select, func
    total = db.scalar(select(func.count()).select_from(Lead).where(*filters)) or 0
    leads = db.scalars(
        select(Lead).where(*filters).order_by(Lead.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return PaginatedResponse(
        items=[LeadResponse.model_validate(l) for l in leads],
        total=total, page=page, page_size=page_size,
    )


@router.get("/filter-options")
def lead_filter_options(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    scope = _lead_scope_filter(current_user)
    filters = [Lead.deleted_at.is_(None), scope] if scope is not None else [Lead.deleted_at.is_(None)]
    from sqlalchemy import select, func
    from database.models import Product, User
    countries = [r[0] for r in db.execute(select(func.distinct(Lead.country)).where(*filters, Lead.country.isnot(None))).all()]
    priorities = [r[0] for r in db.execute(select(func.distinct(Lead.priority_level)).where(*filters, Lead.priority_level.isnot(None))).all()]
    # Get assigned names from users table (full names, not truncated CSV values)
    assigned = [r[0] for r in db.execute(
        select(User.full_name).where(User.role.in_(["Salesperson", "Manager", "Admin"]), User.is_active.is_(True))
    ).all()]
    # Get product names for filtering
    product_names = [r[0] for r in db.execute(select(Product.name).where(Product.is_active.is_(True)).order_by(Product.name)).all()]
    return {
        "countries": sorted(set(c for c in countries if c)),
        "priorities": sorted(set(p for p in priorities if p)),
        "assigned": sorted(set(a for a in assigned if a)),
        "products": product_names,
    }


@router.get("/search")
def search_leads(
    q: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = CRMService(db)
    scope = _lead_scope_filter(current_user)
    from sqlalchemy import select, func, or_
    filters = [Lead.deleted_at.is_(None)]
    if scope is not None:
        filters.append(scope)
    pattern = f"%{q}%"
    filters.append(or_(
        Lead.company_name.ilike(pattern),
        Lead.contact_person.ilike(pattern),
        Lead.email.ilike(pattern),
        Lead.phone.ilike(pattern),
        Lead.lead_id.ilike(pattern),
        Lead.country.ilike(pattern),
        Lead.assigned_to.ilike(pattern),
    ))
    total = db.scalar(select(func.count()).select_from(Lead).where(*filters)) or 0
    leads = db.scalars(
        select(Lead).where(*filters).order_by(Lead.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return PaginatedResponse(
        items=[LeadResponse.model_validate(l) for l in leads],
        total=total, page=page, page_size=page_size,
    )


@router.get("/{lead_id}", response_model=LeadResponse)
def get_lead(lead_id: str, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    lead = db.get(Lead, lead_id)
    if lead is None or lead.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    _check_lead_access(lead, current_user)
    return LeadResponse.model_validate(lead)


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_lead(body: LeadCreate, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    service = CRMService(db)
    payload = body.model_dump(exclude_none=True)
    payload["next_follow_up"] = payload.pop("next_follow_up", None)
    payload["followup_mode"] = payload.pop("followup_mode", None)
    payload["last_discussion"] = payload.pop("last_discussion", None)
    payload["next_action"] = payload.pop("next_action", None)
    # Auto-assign to current user if not explicitly provided
    if not payload.get("assigned_to"):
        payload["assigned_to"] = current_user.get("full_name", current_user.get("username", ""))
    result = service.save_lead_from_entry(payload, current_user)
    if not result.ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.message)
    return {"lead_id": result.lead_id, "message": result.message}


@router.put("/{lead_id}")
def update_lead(lead_id: str, body: LeadUpdate, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    service = CRMService(db)
    lead = db.get(Lead, lead_id)
    if lead is None or lead.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    _check_lead_access(lead, current_user)
    payload = body.model_dump(exclude_none=True)
    if not payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    changes = service.edit_lead_fields(lead_id, payload, current_user)
    return {"changes": changes}


@router.delete("/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lead(lead_id: str, reason: str | None = Query(None), current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    lead = db.get(Lead, lead_id)
    if lead is None or lead.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    _check_lead_access(lead, current_user)
    service = CRMService(db)
    ok = service.delete_lead_logged(lead_id, current_user, reason=reason)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")


@router.put("/{lead_id}/transfer")
def transfer_lead(lead_id: str, body: LeadTransfer, current_user: dict = Depends(require_role(["Admin", "Manager"])), db: Session = Depends(get_db)):
    service = CRMService(db)
    lead = db.get(Lead, lead_id)
    if lead is None or lead.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    ok = service.transfer_lead(lead_id, body.new_owner, current_user, reason=body.reason)
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Transfer failed")
    return {"message": "Lead transferred"}


@router.put("/{lead_id}/reschedule")
def reschedule_followup(lead_id: str, body: RescheduleRequest, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    lead = db.get(Lead, lead_id)
    if lead is None or lead.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    _check_lead_access(lead, current_user)
    service = CRMService(db)
    service.reschedule_followup(lead_id, body.new_date, current_user, note=body.note)
    return {"message": "Follow-up rescheduled"}


@router.post("/{lead_id}/notes")
def add_note(lead_id: str, body: NoteRequest, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    lead = db.get(Lead, lead_id)
    if lead is None or lead.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    _check_lead_access(lead, current_user)
    service = CRMService(db)
    service.append_note(lead_id, body.note, current_user)
    return {"message": "Note added"}


@router.post("/{lead_id}/quick-followup")
def quick_followup(lead_id: str, body: QuickFollowup, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    lead = db.get(Lead, lead_id)
    if lead is None or lead.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    _check_lead_access(lead, current_user)
    service = CRMService(db)
    service.add_quick_followup(lead_id, body.model_dump(exclude_none=True), current_user)
    return {"message": "Follow-up recorded"}


@router.get("/{lead_id}/followups", response_model=list[FollowUpResponse])
def lead_followups(lead_id: str, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    lead = db.get(Lead, lead_id)
    if lead is None or lead.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    _check_lead_access(lead, current_user)
    from database.models import FollowUp
    from sqlalchemy import select
    fups = db.scalars(
        select(FollowUp).where(FollowUp.lead_id == lead_id).order_by(FollowUp.created_at.desc())
    ).all()
    return [FollowUpResponse.model_validate(f) for f in fups]


@router.post("/duplicate-check", response_model=list[DuplicateCheckResult])
def check_duplicates(body: LeadCreate, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    service = CRMService(db)
    payload = body.model_dump(exclude_none=True)
    duplicates = service.find_duplicates(payload)
    return [DuplicateCheckResult(**d) for d in duplicates]


def _lead_scope_filter(user: dict):
    from sqlalchemy import and_, func
    from database.models import Lead
    if user.get("role") == "Salesperson":
        name = (user.get("full_name") or "").strip()
        return and_(Lead.assigned_to.isnot(None), func.lower(Lead.assigned_to) == name.lower())
    return None


def _check_lead_access(lead: Lead, user: dict) -> None:
    if user.get("role") in ("Admin", "Manager"):
        return
    name = (user.get("full_name") or "").strip()
    if not lead.assigned_to or lead.assigned_to.strip().lower() != name.lower():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this lead")
