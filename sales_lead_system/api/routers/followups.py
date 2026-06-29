"""Follow-ups and tasks router."""

from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from api.deps import get_current_user, get_db
from api.schemas import (ActivityWizardRequest, ActivityWizardResponse, FollowUpComplete,
                         FollowUpCompleteResponse, FollowUpCreate, FollowUpResponse, TaskQueue)
from database.crud import FollowUpCRUD
from database.models import ActivityLog, FollowUp, Lead
from modules import activity_engine, task_engine

router = APIRouter()

VALID_LEAD_STATUSES = frozenset({
    "Prospect", "Requirement Qualified", "Technical Discussion",
    "Quotation Sent", "Sample Sent", "Negotiation", "Trial Order",
    "Nurturing", "Order Closed", "Lost",
})

# ── Sprint 3 — Next action templates ─────────────────────────────────────────

NEXT_ACTION_TEMPLATES: dict[str, str] = {
    "Call Again": "Follow-Up Call",
    "Send Quotation": "Send Quotation",
    "Await Customer Response": "Check Customer Response",
    "Schedule Meeting": "Conduct Meeting",
    "Send Samples": "Follow Up On Samples",
    "Request Procurement Information": "Review Procurement Response",
    "Other": "Follow-Up",
}

NO_FOLLOWUP_ACTION = "No Follow-Up Required"

STATUS_SUGGESTED_ACTIONS: dict[str, str] = {
    "Prospect": "Call Again",
    "Requirement Qualified": "Send Quotation",
    "Technical Discussion": "Call Again",
    "Quotation Sent": "Await Customer Response",
    "Sample Sent": "Call Again",
    "Negotiation": "Call Again",
    "Trial Order": "Call Again",
    "Nurturing": "Call Again",
}


def _check_followup_access(fu: FollowUp, user: dict, db: Session) -> None:
    if user.get("role") in ("Admin", "Manager"):
        return
    lead = db.get(Lead, fu.lead_id)
    if lead is None:
        return
    name = (user.get("full_name") or "").strip()
    if not lead.assigned_to or lead.assigned_to.strip().lower() != name.lower():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this follow-up")


@router.get("/tasks", response_model=TaskQueue)
def task_queue(
    upcoming_days: int = Query(7, ge=1, le=30),
    max_today: int = Query(20, ge=1, le=50),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = task_engine.generate_tasks(
        db, current_user, today=None,
        upcoming_days=upcoming_days, max_today=max_today,
    )
    return TaskQueue(**result)


@router.post("", response_model=FollowUpResponse, status_code=status.HTTP_201_CREATED)
def create_followup(body: FollowUpCreate, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    lead = db.get(Lead, body.lead_id)
    if lead is None or lead.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    _check_followup_access(FollowUp(lead_id=body.lead_id), current_user, db)
    crud = FollowUpCRUD()
    payload = body.model_dump(exclude_none=True)
    payload.pop("updated_by", None)
    payload["updated_by"] = current_user.get("full_name", current_user.get("username", ""))
    fu = crud.add_followup(db, payload)
    return FollowUpResponse.model_validate(fu)


@router.put("/{followup_id}", response_model=FollowUpResponse)
def update_followup(followup_id: int, body: FollowUpCreate, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    crud = FollowUpCRUD()
    fu = db.get(FollowUp, followup_id)
    if fu is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Follow-up not found")
    _check_followup_access(fu, current_user, db)
    payload = body.model_dump(exclude_none=True)
    payload.pop("updated_by", None)
    payload["updated_by"] = current_user.get("full_name", current_user.get("username", ""))
    fu = crud.update_followup(db, followup_id, payload)
    if fu is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Follow-up not found")
    return FollowUpResponse.model_validate(fu)


@router.patch("/{followup_id}/complete", response_model=FollowUpCompleteResponse)
def complete_followup(
    followup_id: int,
    body: FollowUpComplete,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    fu = db.get(FollowUp, followup_id)
    if fu is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Follow-up not found")
    _check_followup_access(fu, current_user, db)
    if not body.outcome_notes.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Outcome notes are required")

    now = datetime.now()
    today = now.date()
    user_name = current_user.get("full_name", current_user.get("username", ""))

    fu.outcome_notes = body.outcome_notes.strip()
    fu.completed_at = now
    fu.completed_by = user_name

    if body.discussion_summary is not None:
        fu.discussion = body.discussion_summary.strip()

    db.flush()

    lead = db.get(Lead, fu.lead_id)
    lead_updates = []
    old_status = lead.status

    if body.lead_status is not None and body.lead_status != lead.status:
        if body.lead_status not in VALID_LEAD_STATUSES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid lead status: {body.lead_status}")
        lead.status = body.lead_status
        lead_updates.append(f"Status: {old_status} \u2192 {body.lead_status}")

    if body.interest_level is not None:
        lead.interest_level = body.interest_level
        lead_updates.append(f"Interest: {body.interest_level}")

    if body.potential_deal_value is not None:
        lead.potential_deal_value = body.potential_deal_value
        lead_updates.append(f"Deal: {body.potential_deal_value}")

    if body.customer_requirements is not None:
        lead.customer_requirements = body.customer_requirements
        lead_updates.append("Requirements captured")

    lead.last_contact_date = today

    # ── Auto-create next follow-up ──────────────────────────────────────────
    next_fu: FollowUp | None = None
    has_next_action = (
        body.next_action_type is not None
        and body.next_action_type != NO_FOLLOWUP_ACTION
    )
    is_terminal = lead.status in ("Order Closed", "Lost")

    if has_next_action and body.next_followup_date is not None and not is_terminal:
        template = NEXT_ACTION_TEMPLATES.get(body.next_action_type, "Follow-Up")
        next_fu = FollowUp(
            lead_id=fu.lead_id,
            followup_date=today,
            next_followup=body.next_followup_date,
            discussion=template,
            assigned_to=lead.assigned_to,
            created_at=now,
        )
        db.add(next_fu)
        db.flush()

        lead.has_pending_followup = True

        log_scheduled = ActivityLog(
            action="followup_scheduled",
            user_name=user_name,
            lead_id=fu.lead_id,
            remarks=f"Task: {template} | Due: {body.next_followup_date} | Created automatically",
        )
        db.add(log_scheduled)
    elif is_terminal or (body.next_action_type == NO_FOLLOWUP_ACTION):
        lead.has_pending_followup = False

    db.flush()

    # ── Activity log ────────────────────────────────────────────────────────
    remarks_parts = []
    if lead_updates:
        remarks_parts.append("; ".join(lead_updates))
    remarks_parts.append(f"Outcome: {fu.outcome_notes[:200]}" + ("..." if len(fu.outcome_notes) > 200 else ""))

    log = ActivityLog(
        action="task_completed",
        user_name=user_name,
        lead_id=fu.lead_id,
        remarks=" | ".join(remarks_parts),
    )
    db.add(log)
    db.commit()

    return FollowUpCompleteResponse(
        followup=FollowUpResponse.model_validate(fu),
        next_followup=FollowUpResponse.model_validate(next_fu) if next_fu else None,
    )


@router.post("/{followup_id}/complete-activity", response_model=ActivityWizardResponse)
def complete_activity(
    followup_id: int,
    body: ActivityWizardRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    fu = db.get(FollowUp, followup_id)
    if fu is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Follow-up not found")
    _check_followup_access(fu, current_user, db)
    if not body.actions:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one action must be selected")

    user_name = current_user.get("full_name", current_user.get("username", ""))
    now = datetime.now()
    result = activity_engine.process_activity_wizard(db, fu, body.model_dump(exclude_none=True), user_name, now)

    return ActivityWizardResponse(
        followup_id=result["followup_id"],
        next_followup_id=result["next_followup_id"],
        next_action_type=result["next_action_type"],
        next_action_template=result["next_action_template"],
        next_followup_date=result["next_followup_date"],
        lead_status=result["lead_status"],
        lead_interest=result["lead_interest"],
        lead_updates=result["lead_updates"],
        timeline_entries=result["timeline_entries"],
    )


@router.delete("/{followup_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_followup(followup_id: int, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    fu = db.get(FollowUp, followup_id)
    if fu is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Follow-up not found")
    _check_followup_access(fu, current_user, db)
    db.delete(fu)
