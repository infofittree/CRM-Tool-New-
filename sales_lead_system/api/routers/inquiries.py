"""Inquiry Portal — Salesperson ↔ Procurement commitment workflow."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, update as sql_update
from sqlalchemy.orm import Session as DBSession

from api.deps import get_current_user, get_db
from api.schemas import CommitmentRequest, InquiryCreate, InquiryDetail, InquiryResponse, InquirySummary, InquiryUpdate, RevisionCreate
from database.models import Inquiry, Lead, User, InquiryRevision
from database.models import INQUIRY_COMMITMENT_TYPES

router = APIRouter(tags=["inquiries"])

_INQUIRY_COLS = (
    Inquiry.id,
    Inquiry.lead_id,
    Inquiry.created_by,
    Inquiry.assigned_to,
    Inquiry.title,
    Inquiry.type,
    Inquiry.priority,
    Inquiry.description,
    Inquiry.response,
    Inquiry.status,
    Inquiry.created_at,
    Inquiry.updated_at,
    Inquiry.responded_at,
    Inquiry.commitment_type,
    Inquiry.expected_response_date,
    Inquiry.committed_at,
)


def _row_to_detail(r):
    return InquiryDetail(
        id=r.id, lead_id=r.lead_id, created_by=r.created_by, assigned_to=r.assigned_to,
        title=r.title, type=r.type, priority=r.priority, description=r.description,
        response=r.response, status=r.status, created_at=r.created_at, updated_at=r.updated_at,
        responded_at=r.responded_at, commitment_type=r.commitment_type,
        expected_response_date=r.expected_response_date, committed_at=r.committed_at,
        company_name=getattr(r, "company_name", None),
        contact_person=getattr(r, "contact_person", None),
    )


def _row_to_response(inquiry):
    return InquiryResponse(
        id=inquiry.id, lead_id=inquiry.lead_id, created_by=inquiry.created_by,
        assigned_to=inquiry.assigned_to, title=inquiry.title, type=inquiry.type,
        priority=inquiry.priority, description=inquiry.description, response=inquiry.response,
        status=inquiry.status, created_at=inquiry.created_at, updated_at=inquiry.updated_at,
        responded_at=inquiry.responded_at, commitment_type=inquiry.commitment_type,
        expected_response_date=inquiry.expected_response_date, committed_at=inquiry.committed_at,
    )


@router.get("/inquiries/summary", response_model=InquirySummary)
def inquiry_summary(
    user: dict = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    """Dashboard widget data for inquiry commitments."""
    now = datetime.now(timezone.utc)
    base = select(Inquiry)
    if user["role"] == "Salesperson":
        base = base.where(Inquiry.created_by == user["full_name"])
    elif user["role"] == "Manager":
        base = base.where(
            (Inquiry.assigned_to == user["full_name"]) | (Inquiry.created_by == user["full_name"])
        )
    all_inquiries = db.execute(base).scalars().all()

    total_open = 0
    eod_committed = 0
    pending_response = 0
    overdue = 0
    responded_today = 0
    today = now.date()

    for i in all_inquiries:
        if i.status == "OPEN":
            total_open += 1
        elif i.status == "EOD_COMMITTED":
            eod_committed += 1
        elif i.status == "PENDING_RESPONSE":
            if i.expected_response_date and i.expected_response_date.date() < today:
                overdue += 1
            else:
                pending_response += 1
        elif i.status == "OVERDUE":
            overdue += 1
        if i.responded_at and i.responded_at.date() == today:
            responded_today += 1

    return InquirySummary(
        total_open=total_open,
        eod_committed=eod_committed,
        pending_response=pending_response,
        overdue=overdue,
        responded_today=responded_today,
    )


@router.get("/inquiries", response_model=list[InquiryDetail])
def list_inquiries(
    lead_id: str = Query(None),
    status: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    user: dict = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    q = (
        select(*_INQUIRY_COLS, Lead.company_name, Lead.contact_person)
        .outerjoin(Lead, Lead.lead_id == Inquiry.lead_id)
        .order_by(Inquiry.created_at.desc())
    )
    if user["role"] in ("Admin", "Procurement"):
        pass
    elif user["role"] == "Manager":
        q = q.where((Inquiry.assigned_to == user["full_name"]) | (Inquiry.created_by == user["full_name"]))
    elif user["role"] == "Salesperson":
        q = q.where(Inquiry.created_by == user["full_name"])
    if lead_id:
        q = q.where(Inquiry.lead_id == lead_id)
    if status:
        q = q.where(Inquiry.status == status)
    offset = (page - 1) * page_size
    rows = db.execute(q.offset(offset).limit(page_size)).all()
    return [_row_to_detail(r) for r in rows]


@router.post("/inquiries", response_model=InquiryResponse, status_code=201)
def create_inquiry(
    body: InquiryCreate,
    user: dict = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    if user["role"] not in ("Admin", "Manager", "Salesperson", "Procurement"):
        raise HTTPException(403, "Insufficient permissions")
    lead = db.execute(select(Lead).where(Lead.lead_id == body.lead_id)).scalar_one_or_none()
    if not lead:
        raise HTTPException(404, "Lead not found")
    if user["role"] == "Salesperson" and lead.assigned_to != user["full_name"]:
        raise HTTPException(403, "You can only create inquiries for your own leads")
    procurement_user = db.execute(
        select(User).where(User.role == "Procurement", User.is_active.is_(True))
    ).scalar_one_or_none()
    assigned_to = procurement_user.full_name if procurement_user else (lead.assigned_to or user["full_name"])
    inquiry = Inquiry(
        lead_id=body.lead_id, created_by=user["full_name"], assigned_to=assigned_to,
        title=body.title, type=body.type, priority=body.priority, description=body.description,
    )
    db.add(inquiry)
    db.commit()
    db.refresh(inquiry)

    if body.priority == "URGENT" and procurement_user and procurement_user.phone:
        from modules.notifications import send_whatsapp, format_urgent_inquiry_message
        msg = format_urgent_inquiry_message(
            title=body.title,
            inquiry_type=body.type,
            created_by=user["full_name"],
            lead_id=body.lead_id,
            company_name=lead.company_name,
            description=body.description,
        )
        send_whatsapp(procurement_user.phone, msg)

    return _row_to_response(inquiry)


@router.put("/inquiries/{inquiry_id}", response_model=InquiryResponse)
def update_inquiry(
    inquiry_id: int,
    body: InquiryUpdate,
    user: dict = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    if user["role"] not in ("Admin", "Manager", "Procurement"):
        raise HTTPException(403, "Only Admin, Manager, or Procurement can respond")
    inquiry = db.execute(select(Inquiry).where(Inquiry.id == inquiry_id)).scalar_one_or_none()
    if not inquiry:
        raise HTTPException(404, "Inquiry not found")
    if body.response is not None:
        inquiry.response = body.response
        inquiry.responded_at = func.now()
        inquiry.status = "RESPONDED"
    if body.status is not None:
        inquiry.status = body.status
    db.commit()
    db.refresh(inquiry)
    return _row_to_response(inquiry)


@router.post("/inquiries/{inquiry_id}/commit", response_model=InquiryResponse)
def commit_inquiry(
    inquiry_id: int,
    body: CommitmentRequest,
    user: dict = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    if user["role"] not in ("Admin", "Manager", "Procurement"):
        raise HTTPException(403, "Only Admin, Manager, or Procurement can commit")
    if body.commitment_type not in INQUIRY_COMMITMENT_TYPES:
        raise HTTPException(400, f"Invalid commitment_type. Must be one of {INQUIRY_COMMITMENT_TYPES}")
    inquiry = db.execute(select(Inquiry).where(Inquiry.id == inquiry_id)).scalar_one_or_none()
    if not inquiry:
        raise HTTPException(404, "Inquiry not found")
    if inquiry.status not in ("OPEN", "EOD_COMMITTED", "PENDING_RESPONSE", "OVERDUE"):
        raise HTTPException(400, "Inquiry is already resolved or closed")

    now = func.now()
    inquiry.commitment_type = body.commitment_type
    inquiry.committed_at = now

    if body.commitment_type == "ANSWER_NOW":
        inquiry.status = "RESPONDED"
        inquiry.responded_at = now
        inquiry.response = body.response or ""
    elif body.commitment_type == "BY_EOD":
        inquiry.status = "EOD_COMMITTED"
        inquiry.expected_response_date = None
    elif body.commitment_type == "WILL_TAKE_TIME":
        if not body.expected_response_date:
            raise HTTPException(400, "expected_response_date is required for WILL_TAKE_TIME")
        inquiry.status = "PENDING_RESPONSE"
        inquiry.expected_response_date = body.expected_response_date

    db.commit()
    db.refresh(inquiry)
    return _row_to_response(inquiry)


@router.post("/inquiries/check-overdue")
def check_overdue_inquiries(
    user: dict = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    """Mark overdue EOD and past-date inquiries. Callable by Admin/Procurement."""
    if user["role"] not in ("Admin", "Manager", "Procurement"):
        raise HTTPException(403, "Only Admin, Manager, or Procurement can run overdue check")
    now = datetime.now(timezone.utc)
    today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    updated = {"eod_overdue": 0, "pending_overdue": 0}

    # EOD_COMMITTED inquiries at end of day -> OVERDUE
    eod_count = db.execute(
        select(func.count(Inquiry.id)).where(
            Inquiry.status == "EOD_COMMITTED",
            Inquiry.committed_at < today_end,
        )
    ).scalar()
    if eod_count:
        db.execute(
            sql_update(Inquiry)
            .where(Inquiry.status == "EOD_COMMITTED", Inquiry.committed_at < today_end)
            .values(status="OVERDUE")
        )
        updated["eod_overdue"] = eod_count

    pending_count = db.execute(
        select(func.count(Inquiry.id)).where(
            Inquiry.status == "PENDING_RESPONSE",
            Inquiry.expected_response_date < now,
        )
    ).scalar()
    if pending_count:
        db.execute(
            sql_update(Inquiry)
            .where(Inquiry.status == "PENDING_RESPONSE", Inquiry.expected_response_date < now)
            .values(status="OVERDUE")
        )
        updated["pending_overdue"] = pending_count

    db.commit()
    return {"updated": updated}


# ── Revision / Negotiation endpoints ────────────────────────────────────────

@router.post("/inquiries/{inquiry_id}/revision", response_model=dict, status_code=status.HTTP_201_CREATED)
def request_revision(inquiry_id: int, body: RevisionCreate, user: dict = Depends(get_current_user), db: DBSession = Depends(get_db)):
    """Sales/Manager/Admin requests a revision on a procurement response."""
    inquiry = db.get(Inquiry, inquiry_id)
    if not inquiry:
        raise HTTPException(404, "Inquiry not found")

    # Permission check
    role = user["role"]
    user_name = user["full_name"]
    if role == "Salesperson" and inquiry.created_by != user_name:
        raise HTTPException(403, "You can only request revisions for inquiries you created")
    if role not in ("Admin", "Manager", "Salesperson"):
        raise HTTPException(403, "You do not have permission to request revisions")

    # Must have a response to revise
    if not inquiry.response:
        raise HTTPException(400, "Procurement has not responded yet — nothing to revise")
    if inquiry.status in ("CLOSED",):
        raise HTTPException(400, "Cannot request revision on a closed inquiry")

    # Determine revision number
    latest_rev = db.execute(
        select(func.max(InquiryRevision.revision_number)).where(InquiryRevision.inquiry_id == inquiry_id)
    ).scalar() or 0
    rev_number = latest_rev + 1

    revision = InquiryRevision(
        inquiry_id=inquiry_id,
        revision_number=rev_number,
        created_by=user_name,
        reason=body.reason,
        customer_feedback=body.customer_feedback,
        target_price=body.target_price,
        quantity=body.quantity,
        packaging=body.packaging,
        delivery_timeline=body.delivery_timeline,
        payment_terms=body.payment_terms,
        additional_requirements=body.additional_requirements,
        status="PENDING",
    )
    db.add(revision)

    # Update inquiry status
    inquiry.status = "REVISION_REQUESTED"
    inquiry.updated_at = datetime.now(timezone.utc)

    # Create alert for procurement
    from database.models import CrmAlert
    alert = CrmAlert(
        lead_id=inquiry.lead_id,
        alert_type="revision_requested",
        message=f"Revision requested on \"{inquiry.title}\" by {user_name} — Reason: {body.reason.replace('_', ' ').title()}",
        assigned_to=inquiry.assigned_to,
    )
    db.add(alert)

    # Log activity
    from database.models import ActivityLog
    log = ActivityLog(action="REVISION_REQUESTED", user_name=user_name, lead_id=inquiry.lead_id, remarks=f"Revision #{rev_number} on inquiry {inquiry_id}: {body.reason}")
    db.add(log)

    db.commit()
    db.refresh(revision)
    return {
        "id": revision.id, "inquiry_id": revision.inquiry_id, "revision_number": revision.revision_number,
        "created_by": revision.created_by, "reason": revision.reason, "status": revision.status,
        "created_at": revision.created_at.isoformat(),
    }


@router.get("/inquiries/{inquiry_id}/revisions")
def list_revisions(inquiry_id: int, user: dict = Depends(get_current_user), db: DBSession = Depends(get_db)):
    """Get all revision rounds for an inquiry."""
    inquiry = db.get(Inquiry, inquiry_id)
    if not inquiry:
        raise HTTPException(404, "Inquiry not found")
    revisions = db.scalars(
        select(InquiryRevision).where(InquiryRevision.inquiry_id == inquiry_id).order_by(InquiryRevision.revision_number)
    ).all()
    return [
        {
            "id": r.id, "inquiry_id": r.inquiry_id, "revision_number": r.revision_number,
            "created_by": r.created_by, "reason": r.reason, "customer_feedback": r.customer_feedback,
            "target_price": r.target_price, "quantity": r.quantity, "packaging": r.packaging,
            "delivery_timeline": r.delivery_timeline, "payment_terms": r.payment_terms,
            "additional_requirements": r.additional_requirements, "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "responded_at": r.responded_at.isoformat() if r.responded_at else None,
            "responded_by": r.responded_by,
        }
        for r in revisions
    ]


@router.post("/inquiries/{inquiry_id}/revisions/{rev_id}/respond", response_model=dict)
def respond_to_revision(inquiry_id: int, rev_id: int, body: dict, user: dict = Depends(get_current_user), db: DBSession = Depends(get_db)):
    """Procurement responds to a revision request."""
    role = user["role"]
    if role not in ("Admin", "Manager", "Procurement"):
        raise HTTPException(403, "Only Procurement/Admin/Manager can respond to revisions")

    revision = db.get(InquiryRevision, rev_id)
    if not revision or revision.inquiry_id != inquiry_id:
        raise HTTPException(404, "Revision not found")
    if revision.status != "PENDING":
        raise HTTPException(400, "This revision has already been responded to")

    inquiry = db.get(Inquiry, inquiry_id)
    if not inquiry:
        raise HTTPException(404, "Inquiry not found")

    now = datetime.now(timezone.utc)
    revision.status = "RESPONDED"
    revision.responded_at = now
    revision.responded_by = user["full_name"]

    # Update inquiry with revised response and status
    if body.get("response"):
        inquiry.response = body["response"]
    inquiry.status = "REVISED_RESPONSE"
    inquiry.responded_at = now
    inquiry.updated_at = now

    # Alert sales
    from database.models import CrmAlert
    alert = CrmAlert(
        lead_id=inquiry.lead_id,
        alert_type="revision_responded",
        message=f"Revised quotation available for \"{inquiry.title}\" — Revision #{revision.revision_number}",
        assigned_to=inquiry.created_by,
    )
    db.add(alert)

    # Log activity
    from database.models import ActivityLog
    log = ActivityLog(action="REVISION_RESPONDED", user_name=user["full_name"], lead_id=inquiry.lead_id, remarks=f"Revision #{revision.revision_number} responded")
    db.add(log)

    db.commit()
    return {"status": "ok", "revision_status": "RESPONDED", "inquiry_status": "REVISED_RESPONSE"}
