"""Dropdown option loading and Google Sheet validation extraction."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import openpyxl

from config.settings import CONFIG_DIR


DROPDOWN_CONFIG_PATH = CONFIG_DIR / "dropdown_options.json"


DEFAULT_OPTIONS: dict[str, list[str]] = {
    # New 10-stage canonical funnel (2026-06-02 restructure)
    "lead_statuses": [
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
    ],
    "lost_reasons": [
        "Price Too High",
        "Existing Supplier",
        "Product Not Available",
        "Price Issues",
        "Certification Concern",
        "Imported Locally",
        "Quality Concern",
        "Not Replying",
    ],
    "lead_categories": ["A", "B", "C"],
    "engagement_frequency": ["Frequent", "Medium", "Low"],
    "followup_statuses": ["Open", "Done", "Delayed"],
    # New standardized lead sources (2026-06-03 patch) — code-controlled
    "lead_sources": ["Go4", "Alibaba", "Trademo", "Dataverse", "AI", "LinkedIn", "Spice Exchange", "Other"],
    "salespersons": ["Yash", "Maruti", "Poonam", "Vaidehi", "Rahul"],
    "transfer_to": ["Yash", "Maruti"],
    "continents": ["Asia", "Africa", "Europe", "North America", "South America", "Oceania", "Antarctica"],
    # Modes: Buyer_Master/Alibaba use "Whatsapp/Calling"; Follow_Up uses "WhatsApp/Call/Meeting" — keep both variants
    "modes": ["Whatsapp", "Email", "Calling", "Other"],
    "followup_modes": ["Call", "Email", "WhatsApp", "Meeting", "Whatsapp", "Calling", "Other"],
    "buyer_tags": ["L1", "L2", "L3", "L4"],
    "probabilities": ["25%", "50%", "75%", "90%"],
    "quotation_statuses": ["Sent", "Hold", "Pending"],
    "payment_statuses": ["Pending", "Advance Received", "Completed"],
    "order_statuses": ["Enquiry", "Quotation Sent", "Negotiation", "Confirmed", "In Production", "Dispatched", "Completed"],
    "followup_stages": ["Follow Up 1", "Follow Up 2", "Follow Up 3", "Follow Up 4", "Follow Up 5", "Follow up 6", "Follow up 7"],
}


def load_dropdown_options() -> dict[str, list[str]]:
    """Load dropdown options with safe defaults."""
    # Code-controlled lists — the JSON (or a stale sheet sync) must NEVER override
    # these. Keeps the funnel, lost reasons, categories, sources, etc. authoritative.
    _CODE_CONTROLLED = {
        "lead_statuses", "lost_reasons", "lead_categories",
        "engagement_frequency", "lead_sources", "continents",
    }
    if not DROPDOWN_CONFIG_PATH.exists():
        return DEFAULT_OPTIONS.copy()
    with DROPDOWN_CONFIG_PATH.open("r", encoding="utf-8") as handle:
        loaded = json.load(handle)
    merged = DEFAULT_OPTIONS.copy()
    for key, values in loaded.items():
        if key in _CODE_CONTROLLED:
            continue  # always use the code default for these
        if isinstance(values, list):
            merged[key] = [str(value) for value in values if str(value).strip()]
    return merged


def option_list(key: str, extra: Iterable[str] | None = None) -> list[str]:
    """Return de-duplicated options while preserving configured order."""
    values = list(load_dropdown_options().get(key, []))
    if extra:
        values.extend(str(value) for value in extra if str(value).strip())
    return _dedupe(values)


def all_allowed_statuses() -> tuple[str, ...]:
    """Return the canonical 10-stage funnel statuses."""
    options = load_dropdown_options()
    return tuple(options.get("lead_statuses", []))


def sync_dropdowns_from_workbook(workbook_path: Path) -> dict[str, list[str]]:
    """Extract known dropdown lists from the latest Google Sheet workbook."""
    if not workbook_path.exists():
        return load_dropdown_options()
    wb = openpyxl.load_workbook(workbook_path, data_only=False)
    extracted: dict[str, list[str]] = {}
    for ws in wb.worksheets:
        for dv in ws.data_validations.dataValidation:
            if dv.type != "list" or not dv.formula1:
                continue
            values = _parse_inline_list(dv.formula1)
            if not values:
                continue
            target = _classify_validation(ws.title.strip(), str(dv.sqref), values)
            if target:
                extracted[target] = _dedupe([*extracted.get(target, []), *values])

    merged = load_dropdown_options()
    merged.update(extracted)
    # CODE-CONTROLLED funnel: the new 10-stage funnel, lost reasons, categories and
    # engagement frequency are owned by the application, NOT the Google Sheet. Always
    # force them back to DEFAULT_OPTIONS so a stale sheet can never reintroduce the
    # old statuses (Active, Negotation, OutReach, etc.).
    for protected in ("lead_statuses", "lost_reasons", "lead_categories", "engagement_frequency", "lead_sources", "continents"):
        merged[protected] = list(DEFAULT_OPTIONS[protected])
    DROPDOWN_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with DROPDOWN_CONFIG_PATH.open("w", encoding="utf-8") as handle:
        json.dump(merged, handle, indent=2)
    return merged


def _parse_inline_list(formula: str) -> list[str]:
    text = formula.strip()
    if not (text.startswith('"') and text.endswith('"')):
        return []
    return [item for item in (part.strip() for part in text[1:-1].split(",")) if item]


def _classify_validation(sheet: str, sqref: str, values: list[str]) -> str | None:
    value_set = set(values)
    if sheet == "Follow_Up" and "J" in sqref and {"Open", "Done", "Delayed"} & value_set:
        return "followup_statuses"
    if sheet == "Order_Tracker" and {"Enquiry", "In Production", "Dispatched"} & value_set:
        return "order_statuses"
    if sheet == "Order_Tracker" and {"Advance Received"} <= value_set:
        return "payment_statuses"
    # Lead statuses — includes all variants; Negotation is treated as Negotiation typo
    if {"Active", "Prospect", "Nurture", "OutReach", "Requirement Understanding", "Negotiation", "Negotation", "Order Closed"} & value_set:
        return "lead_statuses"
    # Lead sources — includes new entries: trade mo, HPP, yellow pages, Data verse, spice exchange
    if {"IndiaMart", "Alibaba", "Go4Buyer", "trade mo", "HPP", "yellow pages", "Data verse"} & value_set:
        return "lead_sources"
    if {"Poonam", "Vaidehi", "Rahul"} & value_set:
        return "salespersons"
    if value_set <= {"Yash", "Maruti"}:
        return "transfer_to"
    if {"Follow Up 1", "Follow Up 2"} & value_set:
        return "followup_stages"
    if {"Asia", "Africa", "GCC"} & value_set:
        return "continents"
    # followup_modes check before modes to prefer Call/Meeting classification
    if {"Call", "Meeting", "WhatsApp"} & value_set:
        return "followup_modes"
    if {"Whatsapp", "Calling"} & value_set:
        return "modes"
    if {"L1", "L2", "L3", "L4"} & value_set:
        return "buyer_tags"
    if {"25%", "50%", "75%", "90%"} & value_set:
        return "probabilities"
    if {"Sent", "Hold"} & value_set:
        return "quotation_statuses"
    return None


def _dedupe(values: Iterable[str]) -> list[str]:
    seen = set()
    output = []
    for value in values:
        text = str(value).strip()
        key = text.casefold()
        if text and key not in seen:
            seen.add(key)
            output.append(text)
    return output
