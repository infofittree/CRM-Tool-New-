"""Enterprise reporting helpers — per-funnel-stage analytics.

Pure functions over a leads dataframe (which already carries standard_status,
lead_score, country, continent, lead_source, lead_category, assigned_to,
last_contact_date) plus a next-follow-up map. No DB writes.
"""

from __future__ import annotations


from datetime import date
from typing import Any

import pandas as pd

from modules.status_taxonomy import CANONICAL_STATUSES
from modules.clock import today as biz_today

# Report definitions: stage → (icon, helptext)
STAGE_REPORTS: dict[str, str] = {
    "Prospect": "Fresh buyers entering the pipeline.",
    "Requirement Qualified": "Validated, product-fit opportunities.",
    "Technical Discussion": "Serious buyers in technical/procurement talks.",
    "Quotation Sent": "Awaiting customer response on pricing.",
    "Sample Sent": "Awaiting sample feedback.",
    "Negotiation": "Commercial discussions — closest to closing.",
    "Trial Order": "First/testing orders placed.",
    "Order Closed": "Won business and revenue.",
    "Nurturing": "Long-term opportunities to re-engage.",
    "Lost": "Lost deals and leak analysis.",
}


def attach_followups(leads: pd.DataFrame, followups: pd.DataFrame) -> pd.DataFrame:
    """Add next_followup + follow-up status columns to the leads df."""
    df = leads.copy()
    if df.empty:
        return df
    if not followups.empty and "lead_id" in followups.columns and "next_followup" in followups.columns:
        # Use the latest-entered follow-up per lead (by followup_id), not max date,
        # so a rescheduled-earlier date is respected.
        fu = followups.copy()
        if "followup_id" in fu.columns:
            fu = fu.sort_values("followup_id")
        nxt = fu.dropna(subset=["next_followup"]).groupby("lead_id")["next_followup"].last()
        df["next_followup"] = df["lead_id"].map(nxt)
    else:
        df["next_followup"] = pd.NaT
    today = pd.Timestamp(biz_today())
    nf = pd.to_datetime(df["next_followup"], errors="coerce")
    df["followup_state"] = "None"
    df.loc[nf.notna() & (nf < today), "followup_state"] = "Overdue"
    df.loc[nf.notna() & (nf == today), "followup_state"] = "Due Today"
    df.loc[nf.notna() & (nf > today), "followup_state"] = "Upcoming"
    # Aging: days since last contact
    lc = pd.to_datetime(df.get("last_contact_date"), errors="coerce")
    df["aging_days"] = (today - lc).dt.days
    return df


def apply_filters(df: pd.DataFrame, *, salesperson=None, country=None, continent=None,
                  source=None, category=None, followup_state=None, band=None,
                  date_from=None, date_to=None) -> pd.DataFrame:
    """Apply the standard report filter set."""
    out = df.copy()
    if out.empty:
        return out
    if salesperson:
        out = out[out["assigned_to"].isin(salesperson)]
    if country:
        out = out[out["country"].isin(country)]
    if continent and "continent" in out.columns:
        out = out[out["continent"].isin(continent)]
    if source and "lead_source" in out.columns:
        out = out[out["lead_source"].isin(source)]
    if category and "lead_category" in out.columns:
        out = out[out["lead_category"].isin(category)]
    if followup_state:
        out = out[out["followup_state"].isin(followup_state)]
    if band:
        def _b(s):
            s = float(s or 0)
            return "HOT" if s >= 80 else "WARM" if s >= 55 else "COLD"
        out = out[out["lead_score"].map(_b).isin(band)]
    if date_from and "created_date" in out.columns:
        cd = pd.to_datetime(out["created_date"], errors="coerce")
        out = out[cd >= pd.Timestamp(date_from)]
    if date_to and "created_date" in out.columns:
        cd = pd.to_datetime(out["created_date"], errors="coerce")
        out = out[cd <= pd.Timestamp(date_to)]
    return out


def stage_kpis(df: pd.DataFrame, stage: str) -> dict[str, Any]:
    """Compute KPI numbers for a stage report."""
    n = len(df)
    overdue = int((df["followup_state"] == "Overdue").sum()) if "followup_state" in df.columns else 0
    due = int((df["followup_state"] == "Due Today").sum()) if "followup_state" in df.columns else 0
    avg_age = round(df["aging_days"].dropna().mean(), 0) if "aging_days" in df.columns and df["aging_days"].notna().any() else 0
    a_cat = int((df["lead_category"] == "A").sum()) if "lead_category" in df.columns else 0
    avg_score = round(df["lead_score"].dropna().mean(), 1) if "lead_score" in df.columns and df["lead_score"].notna().any() else 0
    return {"count": n, "overdue": overdue, "due_today": due, "avg_age_days": avg_age,
            "a_category": a_cat, "avg_score": avg_score}


def breakdown(df: pd.DataFrame, column: str, top: int = 10) -> pd.DataFrame:
    """Value-count breakdown for a column, as a tidy dataframe."""
    if df.empty or column not in df.columns:
        return pd.DataFrame(columns=[column, "count"])
    out = df[column].fillna("—").value_counts().head(top).reset_index()
    out.columns = [column, "count"]
    return out
