"""Lead Handover (Transfer) router."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.deps import get_current_user, get_db
from api.schemas import HandoverCreate, HandoverResponse
from database.models import ActivityLog, CrmAlert, FollowUp, Inquiry, Lead, LeadHandover, LeadTransfer, User

router = APIRouter()

HANDOVER_REASONS = ("product_expertise", "language", "region", "customer_request", "workload", "leave", "manager_decision", "other")


def _serialize_handover(h: LeadHandover, company_name: str | None = None) -> dict:
    return {
        "id": h.id,
        "lead_id": h.lead_id,
        "from_user": h.from_user,
        "to_user": h.to_user,
        "reason": h.reason,
        "notes": h.notes,
        "status": h.status,
        "requested_at": h.requested_at,
        "responded_at": h.responded_at,
        "responded_by": h.responded_by,
        "created_by": h.created_by,
        "company_name": company_name,
    }


@router.post("/leads/{lead_id}/handover", response_model=HandoverResponse, status_code=status.HTTP_201_CREATED)
def create_handover(lead_id: str, body: HandoverCreate, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    # Validate lead exists
    lead = db.get(Lead, lead_id)
    if lead is None or lead.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Lead not found")

    user_name = current_user.get("full_name", "").strip()
    role = current_user.get("role", "")

    # Permission: Salesperson can only transfer own leads; Admin/Manager can transfer any
    if role == "Salesperson":
        if not lead.assigned_to or lead.assigned_to.strip().lower() != user_name.lower():
            raise HTTPException(status_code=403, detail="You can only transfer leads assigned to you")
    elif role not in ("Admin", "Manager"):
        raise HTTPException(status_code=403, detail="You do not have permission to transfer leads")

    # Cannot transfer completed leads
    if lead.status in ("Order Closed", "Lost"):
        raise HTTPException(status_code=400, detail="Cannot transfer completed or lost leads")

    # Cannot transfer to self
    if body.to_user.strip().lower() == user_name.lower():
        raise HTTPException(status_code=400, detail="Cannot transfer a lead to yourself")

    # Validate recipient exists, is active, is Salesperson
    recipient = db.scalar(select(User).where(User.full_name == body.to_user.strip(), User.is_active.is_(True), User.deleted_at.is_(None)))
    if not recipient:
        raise HTTPException(status_code=400, detail="Recipient not found or inactive")
    if recipient.role not in ("Salesperson", "Manager", "Admin"):
        raise HTTPException(status_code=400, detail="Only salespersons, managers, or admins can receive transfers")

    # Check no pending handover for this lead already
    existing = db.scalar(select(LeadHandover).where(LeadHandover.lead_id == lead_id, LeadHandover.status == "PENDING"))
    if existing:
        raise HTTPException(status_code=400, detail="A transfer request is already pending for this lead")

    # Create handover record
    handover = LeadHandover(
        lead_id=lead_id,
        from_user=lead.assigned_to or user_name,
        to_user=body.to_user.strip(),
        reason=body.reason,
        notes=body.notes,
        status="PENDING",
        created_by=user_name,
    )
    db.add(handover)

    # Create alert for recipient
    alert = CrmAlert(
        lead_id=lead_id,
        alert_type="handover_request",
        message=f"{user_name} wants to transfer {lead.company_name or lead_id} to you — Reason: {body.reason.replace('_', ' ').title()}",
        assigned_to=body.to_user.strip(),
    )
    db.add(alert)

    # Log activity
    log = ActivityLog(action="HANDOVER_REQUESTED", user_name=user_name, lead_id=lead_id, remarks=f"Transfer to {body.to_user} — {body.reason}")
    db.add(log)

    db.flush()
    db.commit()

    return HandoverResponse(**_serialize_handover(handover, lead.company_name))


@router.get("/leads/{lead_id}/handovers", response_model=list[HandoverResponse])
def lead_handover_history(lead_id: str, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(LeadHandover).where(LeadHandover.lead_id == lead_id).order_by(LeadHandover.requested_at.desc())).all()
    lead = db.get(Lead, lead_id)
    company = lead.company_name if lead else None
    return [HandoverResponse(**_serialize_handover(h, company)) for h in rows]


@router.get("/me/handovers", response_model=list[HandoverResponse])
def my_pending_handovers(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user_name = current_user.get("full_name", "").strip()
    rows = db.scalars(
        select(LeadHandover).where(LeadHandover.to_user == user_name, LeadHandover.status == "PENDING").order_by(LeadHandover.requested_at.desc())
    ).all()
    result = []
    for h in rows:
        lead = db.get(Lead, h.lead_id)
        result.append(HandoverResponse(**_serialize_handover(h, lead.company_name if lead else None)))
    return result


@router.post("/handovers/{handover_id}/accept", response_model=HandoverResponse)
def accept_handover(handover_id: int, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    handover = db.get(LeadHandover, handover_id)
    if not handover:
        raise HTTPException(status_code=404, detail="Handover request not found")

    user_name = current_user.get("full_name", "").strip()
    if handover.to_user.lower() != user_name.lower():
        raise HTTPException(status_code=403, detail="You can only accept transfers addressed to you")
    if handover.status != "PENDING":
        raise HTTPException(status_code=400, detail="This transfer has already been processed")

    lead = db.get(Lead, handover.lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    now = datetime.now()
    handover.status = "ACCEPTED"
    handover.responded_at = now
    handover.responded_by = user_name

    old_owner = lead.assigned_to
    new_owner = handover.to_user

    # Transfer lead ownership
    lead.assigned_to = new_owner

    # Transfer follow-ups
    followups = db.scalars(select(FollowUp).where(FollowUp.lead_id == handover.lead_id)).all()
    for fu in followups:
        fu.assigned_to = new_owner

    # Transfer inquiries
    inquiries = db.scalars(select(Inquiry).where(Inquiry.lead_id == handover.lead_id)).all()
    for inq in inquiries:
        inq.assigned_to = new_owner

    # Create LeadTransfer audit record
    lt = LeadTransfer(
        lead_id=handover.lead_id,
        transferred_from=old_owner,
        transferred_to=new_owner,
        reason=f"Handover accepted: {handover.reason}",
        transferred_by=user_name,
    )
    db.add(lt)

    # Alert sender
    alert = CrmAlert(
        lead_id=handover.lead_id,
        alert_type="handover_accepted",
        message=f"{user_name} accepted the transfer of {lead.company_name or handover.lead_id}",
        assigned_to=handover.from_user,
    )
    db.add(alert)

    # Log activity
    log = ActivityLog(action="HANDOVER_ACCEPTED", user_name=user_name, lead_id=handover.lead_id, remarks=f"{old_owner} -> {new_owner} ({handover.reason})")
    db.add(log)

    db.flush()
    db.commit()

    return HandoverResponse(**_serialize_handover(handover, lead.company_name))


@router.post("/handovers/{handover_id}/decline", response_model=HandoverResponse)
def decline_handover(handover_id: int, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    handover = db.get(LeadHandover, handover_id)
    if not handover:
        raise HTTPException(status_code=404, detail="Handover request not found")

    user_name = current_user.get("full_name", "").strip()
    if handover.to_user.lower() != user_name.lower():
        raise HTTPException(status_code=403, detail="You can only decline transfers addressed to you")
    if handover.status != "PENDING":
        raise HTTPException(status_code=400, detail="This transfer has already been processed")

    now = datetime.now()
    handover.status = "DECLINED"
    handover.responded_at = now
    handover.responded_by = user_name

    lead = db.get(Lead, handover.lead_id)

    # Alert sender
    alert = CrmAlert(
        lead_id=handover.lead_id,
        alert_type="handover_declined",
        message=f"{user_name} declined the transfer of {lead.company_name if lead else handover.lead_id}",
        assigned_to=handover.from_user,
    )
    db.add(alert)

    # Log activity
    log = ActivityLog(action="HANDOVER_DECLINED", user_name=user_name, lead_id=handover.lead_id, remarks=f"{user_name} declined transfer from {handover.from_user}")
    db.add(log)

    db.flush()
    db.commit()

    return HandoverResponse(**_serialize_handover(handover, lead.company_name if lead else None))
