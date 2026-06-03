"""Rule-based notes intelligence: read a salesperson note, suggest next action.

Non-destructive and advisory — it never overwrites a manual decision. Returns a
recommended action, a human reason, and a suggested follow-up offset in days.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NoteSuggestion:
    action: str          # Call / WhatsApp / Email / Send Quotation / Move to Nurture ...
    reason: str          # human-readable explanation
    followup_in_days: int  # suggested next-follow-up offset from today
    urgency: str         # HIGH / MEDIUM / LOW


# Ordered rules: first match wins. (keywords, suggestion factory)
_RULES: tuple[tuple[tuple[str, ...], NoteSuggestion], ...] = (
    (("quotation", "quote", "proforma", "pi ", "price list"),
     NoteSuggestion("Send Quotation", "Client asked for a quotation", 0, "HIGH")),
    (("sample",),
     NoteSuggestion("Send Samples", "Client requested samples", 1, "HIGH")),
    (("catalog", "catalogue", "brochure", "product list"),
     NoteSuggestion("Email Catalog", "Client asked for product catalog", 0, "MEDIUM")),
    (("no answer", "no response", "not picking", "didn't pick", "did not pick", "unreachable", "not reachable"),
     NoteSuggestion("Retry Call", "No response on last attempt — retry", 2, "MEDIUM")),
    (("busy", "call later", "call back", "callback", "call me later"),
     NoteSuggestion("Schedule Callback", "Client busy — call back later", 3, "MEDIUM")),
    (("not now", "later", "next month", "after", "future", "not this", "2027"),
     NoteSuggestion("Move to Nurture", "Interested but not now — nurture", 7, "LOW")),
    (("decision maker", "owner not", "manager not", "boss", "not available", "unavailable"),
     NoteSuggestion("Call Next Week", "Decision maker unavailable", 7, "MEDIUM")),
    (("negotiat", "discount", "target price", "best price", "lower price", "counter"),
     NoteSuggestion("Call + WhatsApp", "Active negotiation — push to close", 1, "HIGH")),
    (("interested", "keen", "wants", "looking for", "requirement"),
     NoteSuggestion("Daily Touchpoint", "Interested lead — stay close", 1, "HIGH")),
    (("order", "confirm", "deal done", "purchase", "buy", "ready to"),
     NoteSuggestion("Confirm Order", "Buying signal — confirm the order", 0, "HIGH")),
    (("not interested", "no requirement", "wrong", "spam", "stop"),
     NoteSuggestion("Mark Not Interested", "Negative signal in notes", 30, "LOW")),
    (("meeting", "visit", "demo", "appointment"),
     NoteSuggestion("Prepare Meeting", "Meeting/visit referenced", 1, "HIGH")),
    (("email", "mail"),
     NoteSuggestion("Send Email", "Email follow-up referenced", 1, "MEDIUM")),
    (("whatsapp", "wa ", "msg", "message"),
     NoteSuggestion("Send WhatsApp", "WhatsApp follow-up referenced", 1, "MEDIUM")),
)

_DEFAULT = NoteSuggestion("Follow Up", "Routine follow-up", 3, "MEDIUM")


def suggest_from_note(note: str | None) -> NoteSuggestion:
    """Return a recommended action for a free-text note."""
    if not note or not str(note).strip():
        return _DEFAULT
    text = str(note).strip().lower()
    for keywords, suggestion in _RULES:
        if any(kw in text for kw in keywords):
            return suggestion
    return _DEFAULT
