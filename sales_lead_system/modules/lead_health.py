"""Lead Health Engine — business-rule-driven health classification.

Rules:
  Healthy:     future follow-up exists, activity within 7 days, no overdue tasks
  Attention:   no activity in 7+ days OR no future follow-up
  At Risk:     no activity in 14+ days OR multiple (≥2) overdue tasks
  Stalled:     no activity in 30+ days, not terminal (Won/Lost)
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from database.models import FollowUp
from modules.status_taxonomy import TERMINAL_LOST, TERMINAL_WON


def _days_since(d: date | datetime | None, today: date | None = None) -> int | None:
    if d is None:
        return None
    ref = today or date.today()
    if isinstance(d, datetime):
        d = d.date()
    return (ref - d).days


def compute_lead_health(
    lead: dict[str, Any] | Any,
    followups: list[FollowUp] | None = None,
    today: date | None = None,
) -> str:
    """Return one of: healthy, attention_needed, at_risk, stalled."""
    ref = today or date.today()
    status = getattr(lead, "status", None) if not isinstance(lead, dict) else lead.get("status", None)
    if status in (TERMINAL_WON,) or status in TERMINAL_LOST:
        return "healthy" if status == TERMINAL_WON else "stalled"

    last_contact = getattr(lead, "last_contact_date", None) if not isinstance(lead, dict) else lead.get("last_contact_date", None)
    last_contact_days = _days_since(last_contact, ref)
    has_pending = getattr(lead, "has_pending_followup", None) if not isinstance(lead, dict) else lead.get("has_pending_followup", None)

    has_future_fu = False
    overdue_count = 0
    if followups:
        for fu in followups:
            nf = fu.next_followup
            if nf and nf >= ref and not fu.completed_at:
                has_future_fu = True
            if nf and nf < ref and not fu.completed_at:
                overdue_count += 1
    if has_pending is True:
        has_future_fu = True

    if last_contact_days is not None and last_contact_days >= 30:
        return "stalled"

    if (last_contact_days is not None and last_contact_days >= 14) or overdue_count >= 2:
        return "at_risk"

    if last_contact_days is not None and last_contact_days >= 7:
        return "attention_needed"

    if not has_future_fu:
        return "attention_needed"

    return "healthy"


def get_risk_level(health: str) -> str:
    mapping = {
        "healthy": "low",
        "attention_needed": "medium",
        "at_risk": "high",
        "stalled": "high",
    }
    return mapping.get(health, "medium")


def get_health_warnings(
    lead: dict[str, Any] | Any,
    followups: list[FollowUp] | None = None,
    today: date | None = None,
) -> list[str]:
    ref = today or date.today()
    status = getattr(lead, "status", None) if not isinstance(lead, dict) else lead.get("status", None)
    last_contact = getattr(lead, "last_contact_date", None) if not isinstance(lead, dict) else lead.get("last_contact_date", None)
    last_contact_days = _days_since(last_contact, ref)

    warnings: list[str] = []
    if not last_contact:
        warnings.append("No recorded activity")
    elif last_contact_days and last_contact_days >= 14:
        warnings.append(f"No activity in {last_contact_days} days")
    elif last_contact_days and last_contact_days >= 7:
        warnings.append(f"No activity in {last_contact_days} days")

    has_future_fu = False
    overdue_count = 0
    if followups:
        for fu in followups:
            nf = fu.next_followup
            if nf and nf >= ref and not fu.completed_at:
                has_future_fu = True
            if nf and nf < ref and not fu.completed_at:
                overdue_count += 1
    if not has_future_fu:
        warnings.append("No future follow-up scheduled")
    if overdue_count >= 2:
        warnings.append(f"{overdue_count} overdue follow-ups")
    if status in TERMINAL_LOST:
        warnings.append("Lead marked as Lost")

    return warnings


def compute_pipeline_health(
    leads: list[dict[str, Any] | Any],
    followups_map: dict[str, list[FollowUp]],
    today: date | None = None,
) -> dict[str, int]:
    counts = {"healthy": 0, "attention_needed": 0, "at_risk": 0, "stalled": 0}
    for lead in leads:
        lid = lead["lead_id"] if isinstance(lead, dict) else lead.lead_id
        health = compute_lead_health(lead, followups_map.get(lid), today)
        if health in counts:
            counts[health] += 1
    return counts
