"""New 10-stage sales funnel taxonomy.

The DB now stores canonical values directly (migration ran in phase4).
This module provides:
  - The canonical status list
  - A safe normalisation function (to_canonical) for any stale/legacy values
  - Stage weights and priority rankings used by scoring and task engine
"""

from __future__ import annotations

from typing import Iterable

# ── Canonical statuses ──────────────────────────────────────────────────────
CANONICAL_STATUSES: tuple[str, ...] = (
    "Prospect",
    "Requirement Qualified",
    "Technical Discussion",
    "Quotation Sent",
    "Sample Sent",
    "Negotiation",
    "Trial Order",
    "Order Closed",
    "Nurturing",
    "Lost",
)

# Active funnel stages (used for funnel charts), ordered early → won.
FUNNEL_ORDER: tuple[str, ...] = (
    "Prospect",
    "Requirement Qualified",
    "Technical Discussion",
    "Quotation Sent",
    "Sample Sent",
    "Negotiation",
    "Trial Order",
    "Order Closed",
)

TERMINAL_WON: str = "Order Closed"
TERMINAL_LOST: tuple[str, ...] = ("Lost",)
PARKED: tuple[str, ...] = ("Nurturing",)

# Stage base-score (0–70 component of the 0–100 model).
# Values represent pipeline advancement; used in lead_scoring.py.
STAGE_BASE_SCORE: dict[str, float] = {
    "Prospect": 7.0,
    "Requirement Qualified": 14.0,
    "Technical Discussion": 24.5,
    "Quotation Sent": 35.0,
    "Sample Sent": 45.5,
    "Negotiation": 56.0,
    "Trial Order": 63.0,
    "Order Closed": 70.0,
    "Nurturing": 10.5,
    "Lost": 0.0,
}

# Task-engine priority rank (1 = highest urgency shown first).
STAGE_PRIORITY: dict[str, int] = {
    "Trial Order": 1,
    "Negotiation": 2,
    "Sample Sent": 3,
    "Quotation Sent": 4,
    "Technical Discussion": 5,
    "Requirement Qualified": 6,
    "Prospect": 7,
    "Nurturing": 8,
    "Order Closed": 99,
    "Lost": 99,
}

# Follow-up cadence by stage (days between touches).
STAGE_CADENCE: dict[str, int] = {
    "Trial Order": 1,
    "Negotiation": 1,
    "Sample Sent": 2,
    "Quotation Sent": 2,
    "Technical Discussion": 3,
    "Requirement Qualified": 3,
    "Prospect": 3,
    "Nurturing": 7,
    "Order Closed": 30,
    "Lost": 60,
}

# Recommended action per stage.
STAGE_ACTION: dict[str, str] = {
    "Trial Order": "Call + Confirm Dispatch",
    "Negotiation": "Call + WhatsApp",
    "Sample Sent": "Follow-up on Feedback",
    "Quotation Sent": "WhatsApp Reminder",
    "Technical Discussion": "Call",
    "Requirement Qualified": "Call",
    "Prospect": "Call",
    "Nurturing": "WhatsApp (soft)",
    "Order Closed": "Relationship check-in",
    "Lost": "—",
}

# ── Legacy → canonical mapping ───────────────────────────────────────────────
_LEGACY_MAP: dict[str, str] = {
    # New funnel passthroughs (already canonical)
    "prospect": "Prospect",
    "requirement qualified": "Requirement Qualified",
    "technical discussion": "Technical Discussion",
    "quotation sent": "Quotation Sent",
    "sample sent": "Sample Sent",
    "negotiation": "Negotiation",
    "trial order": "Trial Order",
    "order closed": "Order Closed",
    "nurturing": "Nurturing",
    "lost": "Lost",
    # Old sheet values → new canonical
    "new": "Prospect",
    "new lead": "Prospect",
    "active": "Prospect",
    "outreach": "Prospect",
    "out reach": "Prospect",
    "assigned": "Prospect",
    "contacted": "Prospect",
    "requirement understanding": "Requirement Qualified",
    "interested": "Requirement Qualified",
    "qualified": "Requirement Qualified",
    "meeting scheduled": "Technical Discussion",
    "meeting": "Technical Discussion",
    "negotation": "Negotiation",          # typo
    "negoatiation": "Negotiation",        # typo
    "negotiating": "Negotiation",
    "samples sent": "Sample Sent",
    "sample": "Sample Sent",
    "converted": "Order Closed",
    "won": "Order Closed",
    "order received": "Order Closed",
    "closed won": "Order Closed",
    "nurture": "Nurturing",
    "follow up stage": "Nurturing",
    "follow up": "Nurturing",
    "follow-up": "Nurturing",
    "inactive": "Nurturing",
    "dormant": "Nurturing",
    "no response": "Nurturing",
    "no answer": "Nurturing",
    "not now": "Nurturing",
    "not interested": "Lost",
    "dead": "Lost",
    "closed lost": "Lost",
    "rejected": "Lost",
}
# NOTE: The DB now stores canonical values directly (phase4 migration already
# converted old→new, including old "Prospect"→"Requirement Qualified"). So
# to_canonical must treat "prospect" as a PASSTHROUGH to "Prospect" — no second
# remap. Do not re-add a "prospect": "Requirement Qualified" entry here.

_KEYWORD_FALLBACKS: tuple[tuple[str, str], ...] = (
    ("trial order", "Trial Order"),
    ("trial", "Trial Order"),
    ("negoti", "Negotiation"),
    ("negota", "Negotiation"),
    ("sample sent", "Sample Sent"),
    ("sample", "Sample Sent"),
    ("quotat", "Quotation Sent"),
    ("technical disc", "Technical Discussion"),
    ("tech disc", "Technical Discussion"),
    ("requirement qual", "Requirement Qualified"),
    ("req qual", "Requirement Qualified"),
    ("order clos", "Order Closed"),
    ("convert", "Order Closed"),
    ("nurtur", "Nurturing"),
    ("follow", "Nurturing"),
    ("inactive", "Nurturing"),
    ("lost", "Lost"),
    ("not interest", "Lost"),
    ("interest", "Requirement Qualified"),
    ("prospect", "Prospect"),
)

_DEFAULT = "Prospect"


def to_canonical(raw: str | None) -> str:
    """Normalise any raw/legacy value to a canonical status."""
    if not raw:
        return _DEFAULT
    key = str(raw).strip().casefold()
    if key in _LEGACY_MAP:
        return _LEGACY_MAP[key]
    for needle, canonical in _KEYWORD_FALLBACKS:
        if needle in key:
            return canonical
    return _DEFAULT


# Back-compat alias used by weekly_review, dashboard_queries etc.
to_standard = to_canonical


def is_won(status: str) -> bool:
    return status == TERMINAL_WON


def is_lost(status: str) -> bool:
    return status in TERMINAL_LOST


def is_open(status: str) -> bool:
    return not (is_won(status) or is_lost(status))


def is_active_pipeline(status: str) -> bool:
    """True for stages that need immediate sales attention (not parked/terminal)."""
    return status in FUNNEL_ORDER and status not in (TERMINAL_WON,)


def map_many(values: Iterable[str | None]) -> list[str]:
    return [to_canonical(v) for v in values]
