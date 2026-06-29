"""Activity Workflow Engine — processes wizard data, creates next tasks, updates leads."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from database.models import ActivityLog, EngagementEvent, FollowUp, Lead


def _today() -> date:
    return date.today()


def _parse_date(raw: str | None) -> date | None:
    if not raw:
        return None
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        pass
    mapping = {"tomorrow": _today() + timedelta(days=1), "2_days": _today() + timedelta(days=2), "3_days": _today() + timedelta(days=3)}
    return mapping.get(raw)


INTEREST_MAP = {"interested": "HIGH", "maybe": "MEDIUM", "not_interested": "LOW"}

CALL_OUTCOME_TO_DIRECTION: dict[str, str | None] = {
    "connected": "answered",
    "not_answered": "no_answer",
    "wrong_number": "wrong_number",
    "call_back_later": "call_back_later",
}


def _infer_interest(wizard: dict[str, Any]) -> str | None:
    ci = wizard.get("customer_interest")
    mo = wizard.get("meeting_outcome")
    if ci:
        return INTEREST_MAP.get(ci)
    if mo:
        if mo == "interested":
            return "HIGH"
        if mo in ("needs_proposal", "needs_pricing", "needs_samples"):
            return "HIGH"
        if mo == "not_interested":
            return "LOW"
        return "MEDIUM"
    if wizard.get("not_interested_reason"):
        return "LOW"
    if wizard.get("customer_requirements"):
        return "HIGH"
    return None


def _infer_lead_status(wizard: dict[str, Any], current_status: str) -> str | None:
    ci = wizard.get("customer_interest")
    mo = wizard.get("meeting_outcome")
    reason = wizard.get("not_interested_reason")
    if ci == "not_interested" or reason:
        return "Lost"
    if ci == "interested" or mo == "interested":
        if current_status == "Prospect":
            return "Requirement Qualified"
    if mo == "needs_proposal":
        if current_status in ("Prospect", "Requirement Qualified"):
            return "Technical Discussion"
    if mo == "needs_pricing":
        return "Quotation Sent"
    if mo == "needs_samples":
        return "Sample Sent"
    return None


def _next_action_summary(wizard: dict[str, Any]) -> str:
    actions = wizard.get("actions", [])
    parts = []
    if "call" in actions:
        co = wizard.get("call_outcome", "")
        parts.append(f"Call: {co.replace('_', ' ').title()}")
    if "email" in actions:
        parts.append("Email sent" + (" (response awaited)" if wizard.get("expect_response") else ""))
    if "whatsapp" in actions:
        parts.append("WhatsApp sent" + (" (response awaited)" if wizard.get("expect_response") else ""))
    if "meeting" in actions:
        mo = wizard.get("meeting_outcome", "")
        if mo:
            parts.append(f"Meeting: {mo.replace('_', ' ').title()}")
    if "other" in actions:
        parts.append("Other activity")
    return " | ".join(parts) if parts else "Activity completed"


def _determine_next_task_type(wizard: dict[str, Any]) -> tuple[str | None, str | None, date | None]:
    """Return (next_action_type, template_name, due_date) or (None, None, None) if terminal."""
    actions = wizard.get("actions", [])
    ci = wizard.get("customer_interest")
    co = wizard.get("call_outcome")
    mo = wizard.get("meeting_outcome")
    er = wizard.get("expect_response")
    reason = wizard.get("not_interested_reason")
    fallback_date = _today() + timedelta(days=3)

    # ── Not interested / Lost ──
    if ci == "not_interested" or reason:
        return (None, None, None)

    # ── Call: Not Answered ──
    if "call" in actions and co == "not_answered":
        rcd = _parse_date(wizard.get("response_check_date"))
        return ("Call Again", "Follow-Up Call", rcd or fallback_date)

    # ── Call: Wrong Number ──
    if "call" in actions and co == "wrong_number":
        return (None, None, None)

    # ── Call: Call Back Later ──
    if "call" in actions and co == "call_back_later":
        rcd = _parse_date(wizard.get("response_check_date"))
        return ("Call Again", "Follow-Up Call", rcd or fallback_date)

    # ── Email / WhatsApp / SMS: Response Expected ──
    if er and any(a in actions for a in ("email", "whatsapp")):
        rcd = _parse_date(wizard.get("response_check_date"))
        return ("Await Customer Response", "Check Customer Response", rcd or fallback_date)

    # ── Meeting outcomes ──
    if "meeting" in actions:
        if mo == "interested":
            reqs = wizard.get("customer_requirements", [])
            if "pricing" in reqs or "quotation" in reqs:
                fd = _parse_date(wizard.get("followup_date"))
                return ("Send Quotation", "Send Quotation", fd or fallback_date)
            if "samples" in reqs:
                fd = _parse_date(wizard.get("followup_date"))
                return ("Send Samples", "Follow Up On Samples", fd or fallback_date)
            if "meeting" in reqs:
                fd = _parse_date(wizard.get("followup_date"))
                return ("Schedule Meeting", "Conduct Meeting", fd or fallback_date)
            fd = _parse_date(wizard.get("followup_date"))
            return ("Call Again", "Follow-Up Call", fd or fallback_date)
        if mo in ("needs_proposal", "needs_pricing"):
            fd = _parse_date(wizard.get("followup_date"))
            return ("Send Quotation", "Send Quotation", fd or fallback_date)
        if mo == "needs_samples":
            fd = _parse_date(wizard.get("followup_date"))
            return ("Send Samples", "Follow Up On Samples", fd or fallback_date)
        if mo == "not_interested":
            return (None, None, None)
        fd = _parse_date(wizard.get("followup_date"))
        return ("Call Again", "Follow-Up Call", fd or fallback_date)

    # ── Call: Connected + Interested/Maybe — check requirements ──
    if "call" in actions and co == "connected":
        if ci == "interested" or ci == "maybe":
            reqs = wizard.get("customer_requirements", [])
            if "pricing" in reqs or "quotation" in reqs:
                fd = _parse_date(wizard.get("followup_date"))
                return ("Send Quotation", "Send Quotation", fd or fallback_date)
            if "samples" in reqs:
                fd = _parse_date(wizard.get("followup_date"))
                return ("Send Samples", "Follow Up On Samples", fd or fallback_date)
            if "meeting" in reqs:
                fd = _parse_date(wizard.get("followup_date"))
                return ("Schedule Meeting", "Conduct Meeting", fd or fallback_date)
            fd = _parse_date(wizard.get("followup_date"))
            return ("Call Again", "Follow-Up Call", fd or fallback_date)
        if ci == "maybe":
            fd = _parse_date(wizard.get("followup_date"))
            return ("Call Again", "Follow-Up Call", fd or fallback_date)

    # ── Catch-all for call connected without interest data ──
    if "call" in actions:
        fd = _parse_date(wizard.get("followup_date"))
        return ("Call Again", "Follow-Up Call", fd or fallback_date)

    # ── Other / default ──
    fd = _parse_date(wizard.get("followup_date"))
    if fd:
        return ("Other", "Follow-Up", fd)
    return (None, None, None)


def process_activity_wizard(
    db: Session,
    followup: FollowUp,
    wizard: dict[str, Any],
    user_name: str,
    now: datetime,
) -> dict[str, Any]:
    """Process the complete activity wizard payload.

    Returns a summary dict with lead_updates, next_task info, timeline entries.
    """
    lead = db.get(Lead, followup.lead_id)
    today = now.date()
    actions = wizard.get("actions", [])
    notes_text = (wizard.get("notes") or "").strip()

    # ── 1. Build outcome notes from wizard data ──
    outcome_parts = [_next_action_summary(wizard)]
    if notes_text:
        outcome_parts.append(f"Notes: {notes_text}")
    outcome_notes = " | ".join(outcome_parts)

    # ── 2. Update follow-up record ──
    followup.outcome_notes = outcome_notes
    followup.completed_at = now
    followup.completed_by = user_name

    # ── 3. Update lead ──
    lead_updates: list[str] = []
    old_status = lead.status

    new_status = _infer_lead_status(wizard, lead.status)
    if new_status and new_status != lead.status:
        lead.status = new_status
        lead_updates.append(f"Status: {old_status} → {new_status}")

    new_interest = _infer_interest(wizard)
    if new_interest:
        lead.interest_level = new_interest
        lead_updates.append(f"Interest: {new_interest}")

    reqs = wizard.get("customer_requirements")
    if reqs:
        lead.customer_requirements = ", ".join(reqs)
        lead_updates.append("Requirements captured")

    lead.last_contact_date = today
    lead_updates.append("Last contact updated")

    # ── 4. Create engagement events for each action ──
    timeline_entries: list[str] = []
    for action in actions:
        event_type = "call" if action == "call" else action
        direction = "outbound"
        outcome = None
        notes = None

        if action == "call":
            co = wizard.get("call_outcome")
            outcome = CALL_OUTCOME_TO_DIRECTION.get(co, co) if co else "answered"
            ci = wizard.get("customer_interest")
            if ci:
                notes = f"Customer: {ci.replace('_', ' ').title()}"
            timeline_entries.append(f"Call completed — {outcome.replace('_', ' ').title()}")
        elif action == "email":
            er = wizard.get("expect_response")
            timeline_entries.append("Email sent" + (" (response awaited)" if er else ""))
        elif action == "whatsapp":
            er = wizard.get("expect_response")
            timeline_entries.append("WhatsApp sent" + (" (response awaited)" if er else ""))
        elif action == "meeting":
            mo = wizard.get("meeting_outcome")
            outcome = mo
            timeline_entries.append(f"Meeting completed — {(mo or '').replace('_', ' ').title()}")
        elif action == "other":
            timeline_entries.append("Other activity logged")

        event = EngagementEvent(
            lead_id=lead.lead_id,
            user_name=user_name,
            event_type=event_type,
            channel=event_type,
            direction=direction,
            outcome=outcome,
            notes=notes,
            occurred_at=now,
        )
        db.add(event)

    # ── 5. Determine next task ──
    next_task_type, next_task_template, next_task_date = _determine_next_task_type(wizard)
    next_fu: FollowUp | None = None
    is_terminal = lead.status in ("Order Closed", "Lost")

    if next_task_type and next_task_date and not is_terminal:
        next_fu = FollowUp(
            lead_id=followup.lead_id,
            followup_date=today,
            next_followup=next_task_date,
            discussion=next_task_template or "Follow-Up",
            next_action=next_task_type,
            assigned_to=lead.assigned_to,
            mode=wizard.get("next_followup_mode"),
            created_at=now,
        )
        db.add(next_fu)
        db.flush()

        lead.has_pending_followup = True

        log = ActivityLog(
            action="followup_scheduled",
            user_name=user_name,
            lead_id=followup.lead_id,
            remarks=f"Auto: {next_task_template} | Due: {next_task_date}",
        )
        db.add(log)
        timeline_entries.append(f"Next task created: {next_task_template} ({next_task_date})")
    else:
        lead.has_pending_followup = False

    # ── 6. Create main activity log ──
    action_label = "task_completed"
    main_log = ActivityLog(
        action=action_label,
        user_name=user_name,
        lead_id=followup.lead_id,
        remarks=" | ".join(lead_updates) + f" | {outcome_notes[:200]}",
    )
    db.add(main_log)

    # ── 7. Create rich timeline entries ──
    for entry in timeline_entries:
        tl = ActivityLog(
            action="activity_log",
            user_name=user_name,
            lead_id=followup.lead_id,
            remarks=entry,
        )
        db.add(tl)

    db.commit()

    return {
        "lead_updates": lead_updates,
        "lead_status": lead.status,
        "lead_interest": lead.interest_level,
        "followup_id": followup.followup_id,
        "next_followup_id": next_fu.followup_id if next_fu else None,
        "next_action_type": next_task_type,
        "next_action_template": next_task_template,
        "next_followup_date": str(next_task_date) if next_task_date else None,
        "timeline_entries": timeline_entries,
    }
