"""Lead Health Score engine — new 10-stage funnel model (Phase 4).

Score = stage_base(0-70) + category(0-20) + engagement_frequency(0-10)  →  0-100

HOT  ≥ 80   (Trial Order/Negotiation with A-category)
WARM 55-79  (Quotation/Sample/Tech-Discussion with B+)
COLD  < 55  (Prospect/Requirement/Nurturing/low-category)

Formula is intentionally transparent and explainable to the sales team.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from modules.status_taxonomy import STAGE_BASE_SCORE, to_canonical

# Band thresholds
BAND_HOT = 80
BAND_WARM = 55

# Category → additional points (max 20)
_CATEGORY_POINTS: dict[str, float] = {
    "A": 20.0,
    "B": 10.0,
    "C": 0.0,
}

# Buyer engagement frequency → additional points (max 10)
_ENGAGEMENT_POINTS: dict[str, float] = {
    "Frequent": 10.0,
    "Medium": 5.0,
    "Low": 0.0,
}

# Alibaba buyer level → small bonus (max 5). Deliberately the SMALLEST factor so
# it never out-weighs funnel stage, category, or engagement (priority order).
_ALIBABA_LEVEL_POINTS: dict[str, float] = {
    "L4": 5.0,
    "L3": 4.0,
    "L2": 2.0,
    "L1": 1.0,
}


def _as_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return datetime.fromisoformat(str(value)[:10]).date()
    except (ValueError, TypeError):
        return None


# Alibaba buyer level → suggested lead category (smart default, overridable)
_ALIBABA_LEVEL_TO_CATEGORY: dict[str, str] = {
    "L4": "A", "L3": "A", "L2": "B", "L1": "C",
}


def suggest_category_from_alibaba_level(level: str | None) -> str | None:
    """Return the recommended A/B/C for an Alibaba buyer level (or None)."""
    if not level:
        return None
    return _ALIBABA_LEVEL_TO_CATEGORY.get(str(level).strip().upper())


def band_for_score(score: float) -> str:
    if score >= BAND_HOT:
        return "HOT"
    if score >= BAND_WARM:
        return "WARM"
    return "COLD"


def band_emoji(band: str) -> str:
    return {"HOT": "🔥", "WARM": "🟠", "COLD": "🔵"}.get(band, "")


def score_lead(lead: dict[str, Any], **_kwargs) -> tuple[float, str, dict[str, float]]:
    """Return (score 0-100, band, breakdown) for one lead dict.

    Extra kwargs are accepted and silently ignored for backward compat with
    call-sites that pass followup_count / event_count / has_future_followup.
    """
    breakdown: dict[str, float] = {}

    # 1. Stage base score (0-70) — dominant component
    status = to_canonical(lead.get("status"))
    breakdown["stage"] = STAGE_BASE_SCORE.get(status, 7.0)

    # 2. Lead category (0-20)
    category = str(lead.get("lead_category") or "").strip().upper()
    breakdown["category"] = _CATEGORY_POINTS.get(category, 0.0)

    # 3. Buyer engagement frequency (0-10)
    freq = str(lead.get("buyer_engagement_frequency") or "").strip().title()
    breakdown["engagement_freq"] = _ENGAGEMENT_POINTS.get(freq, 0.0)

    # 4. Alibaba buyer level (0-5) — only for Alibaba leads, smallest factor
    if str(lead.get("lead_source") or "").strip().lower() == "alibaba":
        level = str(lead.get("buyer_tag") or "").strip().upper()
        breakdown["alibaba_level"] = _ALIBABA_LEVEL_POINTS.get(level, 0.0)

    score = max(0.0, min(100.0, round(sum(breakdown.values()), 1)))
    return score, band_for_score(score), breakdown


def recompute_all_scores(session) -> int:
    """Recompute and persist lead_score for every non-deleted lead.

    Reads category + engagement_frequency from DB — the new fields must exist
    (phase4 migration runs before scoring). Safe to re-run.
    """
    from sqlalchemy import select
    from database.models import Lead

    updated = 0
    for lead in session.scalars(select(Lead).where(Lead.deleted_at.is_(None))).all():
        lead_dict = {col.name: getattr(lead, col.name) for col in Lead.__table__.columns}
        score, _band, _bd = score_lead(lead_dict)
        if lead.lead_score != score:
            lead.lead_score = score
            updated += 1
    return updated
