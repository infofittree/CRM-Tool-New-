"""Weekly Sales Intelligence engine.

Powers the Weekly Review page. Pure, read-only aggregation over leads,
engagement_events, followups, and activity_logs for a Monday→Sunday window
(configurable). Degrades gracefully when a week has little history — numbers are
real, never fabricated, and populate richer as the team logs activity.

This module does not modify any data and does not touch scoring / task / follow-up
logic; it only reads.
"""

from __future__ import annotations


from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from database.models import ActivityLog, EngagementEvent, FollowUp, Lead
from modules.lead_scoring import band_for_score
from modules.status_taxonomy import is_lost, is_open, is_won, to_standard
from modules.clock import today as biz_today

# ---- communication event types ----
_CALL = {"call"}
_WHATSAPP = {"whatsapp"}
_EMAIL = {"email"}
_MEETING = {"meeting"}
_NOTE = {"note"}
_FOLLOWUP = {"followup"}

# Loss-reason keyword patterns mined from notes.
_LOSS_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Price / Budget", ("price", "expensive", "costly", "budget", "high rate", "target price", "cheap")),
    ("No Response", ("no response", "no answer", "not picking", "unreachable", "not replying", "no reply")),
    ("Wrong Contact", ("wrong number", "wrong contact", "not decision", "decision maker", "not concerned")),
    ("Competitor", ("competitor", "other supplier", "already buying", "another vendor")),
    ("Timing", ("not now", "next year", "later", "future", "2027", "timing")),
    ("Low Interest", ("not interested", "no requirement", "low interest", "just asking")),
    ("Quality / Specs", ("quality", "specification", "spec", "sample not")),
)


# --------------------------------------------------------------------------- #
# Week helpers
# --------------------------------------------------------------------------- #
def week_bounds(reference: date | None = None, offset_weeks: int = 0) -> tuple[date, date]:
    """Return (monday, sunday) for the week containing reference + offset."""
    reference = reference or biz_today()
    monday = reference - timedelta(days=reference.weekday()) + timedelta(weeks=offset_weeks)
    return monday, monday + timedelta(days=6)


def _dt_start(d: date) -> datetime:
    return datetime.combine(d, time.min)


def _dt_end(d: date) -> datetime:
    return datetime.combine(d, time.max)


def _scope(user: dict[str, Any]):
    base = Lead.deleted_at.is_(None)
    if user.get("role") == "Salesperson":
        name = (user.get("full_name") or "").strip()
        return and_(base, or_(Lead.assigned_to == name.upper(), Lead.assigned_to == name.lower()))
    return base


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


def _group_by_owner(leads: list[Lead]) -> tuple[dict[str, list[Lead]], dict[str, str]]:
    """Group leads by a case/space-insensitive owner key so 'Rahul' and 'RAHUL'
    are one person. Returns (groups keyed by canonical key, display-name map).

    The display name is the most common original spelling for that owner, matching
    how the rest of the CRM treats owners (lower+trim) and avoiding duplicate
    leaderboard rows for the same human.
    """
    groups: dict[str, list[Lead]] = defaultdict(list)
    spellings: dict[str, Counter] = defaultdict(Counter)
    for l in leads:
        raw = (l.assigned_to or "Unassigned").strip()
        key = raw.lower()
        groups[key].append(l)
        spellings[key][raw] += 1
    display = {k: c.most_common(1)[0][0] for k, c in spellings.items()}
    return groups, display


def _latest_followup_map(session: Session, scope=None) -> dict[str, Any]:
    """Map lead_id -> next_followup using SQL MAX(followup_id) per lead.

    Single SQL aggregation instead of iterating every follow-up row in Python.
    """
    latest = func.max(FollowUp.followup_id)
    subq = (
        select(FollowUp.lead_id, func.max(FollowUp.followup_id).label("max_id"))
    )
    if scope is not None:
        subq = subq.join(Lead).where(scope)
    subq = subq.group_by(FollowUp.lead_id).subquery()

    stmt = select(FollowUp.lead_id, FollowUp.next_followup).join(
        subq, and_(FollowUp.lead_id == subq.c.lead_id, FollowUp.followup_id == subq.c.max_id)
    )
    return {lid: nf for lid, nf in session.execute(stmt).all() if nf}


# --------------------------------------------------------------------------- #
# Raw weekly activity collection (shared by all sections)
# --------------------------------------------------------------------------- #
# Audit actions that are system noise (not real sales activity) — excluded from
# timeline and never counted as work.
_AUDIT_NOISE = {"IMPORT_LEAD", "UPDATE_FROM_EXCEL", "SYNC", "STARTUP"}


def _collect_week_activity(session: Session, lead_ids: set[str], start: date, end: date) -> dict[str, list[dict]]:
    """Return per-lead chronological activity within the week.

    Real sales activity comes from engagement_events (occurred_at) and followups
    (by their actual followup_date, not import time). Audit logs are included for
    the timeline only (tagged source='audit') and are never counted as work, so
    bulk-import timestamps cannot inflate weekly metrics.
    """
    s, e = _dt_start(start), _dt_end(end)
    per_lead: dict[str, list[dict]] = defaultdict(list)

    if lead_ids:
        for ev in session.scalars(
            select(EngagementEvent).where(
                EngagementEvent.occurred_at >= s, EngagementEvent.occurred_at <= e,
                EngagementEvent.lead_id.in_(lead_ids),
            )
        ):
            per_lead[ev.lead_id].append({
                "when": ev.occurred_at, "source": "engagement", "type": ev.event_type,
                "user": ev.user_name, "text": ev.notes or "",
            })
        for fu in session.scalars(
            select(FollowUp).where(
                FollowUp.followup_date >= start, FollowUp.followup_date <= end,
                FollowUp.lead_id.in_(lead_ids),
            )
        ):
            when = datetime.combine(fu.followup_date, time(12, 0)) if fu.followup_date else fu.created_at
            per_lead[fu.lead_id].append({
                "when": when, "source": "followup", "type": (fu.mode or "followup").lower(),
                "user": fu.updated_by or fu.assigned_to, "text": fu.discussion or fu.next_action or "",
            })
        for al in session.scalars(
            select(ActivityLog).where(
                ActivityLog.timestamp >= s, ActivityLog.timestamp <= e,
                ActivityLog.lead_id.in_(lead_ids),
                or_(ActivityLog.action.is_(None), ~ActivityLog.action.in_(_AUDIT_NOISE)),
            )
        ):
            per_lead[al.lead_id].append({
                "when": al.timestamp, "source": "audit", "type": al.action,
                "user": al.user_name, "text": al.remarks or "",
            })
    for lid in per_lead:
        per_lead[lid].sort(key=lambda a: a["when"] or datetime.min)
    return per_lead


def _classify_activity_counts(activities: list[dict]) -> dict[str, int]:
    """Count real work only, counting each action exactly once.

    The FollowUp table is the single source of truth for a contact action and its
    channel (mode). Every quick follow-up also writes a mirror engagement_event
    (call/whatsapp/email/meeting/followup) for the dashboard's live panels — those
    mirrors must NOT be counted here or each action is double-counted. From
    engagement_events we therefore count only standalone signals (note/reply/
    inbound) that have no FollowUp row. Audit rows are never counted.
    """
    counts = {"calls": 0, "whatsapp": 0, "emails": 0, "meetings": 0, "notes": 0, "followups": 0, "total": 0}
    for a in activities:
        if a["source"] == "audit":
            continue  # audit trail is for the timeline, not for work metrics
        t = (a["type"] or "").lower()
        if a["source"] == "followup":
            counts["followups"] += 1
            counts["total"] += 1
            if "call" in t:
                counts["calls"] += 1
            elif "whatsapp" in t:
                counts["whatsapp"] += 1
            elif "email" in t:
                counts["emails"] += 1
            elif "meeting" in t:
                counts["meetings"] += 1
            continue
        # engagement events: only count standalone signals, never the call/whatsapp/
        # email/meeting/followup mirrors of a FollowUp row (avoids double counting).
        if t in _NOTE or "note" in t or t in ("reply", "inbound"):
            counts["notes"] += 1
            counts["total"] += 1
        # everything else (call/whatsapp/email/meeting/followup mirror,
        # status_change, category_change, field_edit) — not counted here.
    return counts


# --------------------------------------------------------------------------- #
# Section 1 — Weekly overview
# --------------------------------------------------------------------------- #
def weekly_overview(session: Session, user: dict[str, Any], start: date, end: date) -> dict[str, Any]:
    leads = session.scalars(select(Lead).where(_scope(user))).all()
    lead_ids = {l.lead_id for l in leads}
    acts = _collect_week_activity(session, lead_ids, start, end)

    agg = Counter()
    contacted = set()
    for lid, items in acts.items():
        c = _classify_activity_counts(items)
        for k, v in c.items():
            agg[k] += v
        if c["total"] > 0:
            contacted.add(lid)

    today = biz_today()
    pending = overdue = 0
    bands = Counter()
    statuses = Counter()
    for l in leads:
        std = to_standard(l.status)
        statuses[std] += 1
        bands[band_for_score(float(l.lead_score or 0))] += 1

    # Pending / overdue follow-ups — latest-ENTERED follow-up per lead (consistent
    # with the dashboard and task engine; not max()).
    fu_next = _latest_followup_map(session, _scope(user))
    for lid, nxt in fu_next.items():
        if lid not in lead_ids:
            continue
        nd = _as_date(nxt)
        if nd is None:
            continue
        if nd < today:
            overdue += 1
        elif nd >= today:
            pending += 1

    # Conversions this week: status_change events ending in a won status, in window
    s, e = _dt_start(start), _dt_end(end)
    conversions_week = lost_week = 0
    for ev in session.scalars(select(EngagementEvent).where(
        EngagementEvent.event_type == "status_change", EngagementEvent.occurred_at >= s, EngagementEvent.occurred_at <= e
    )):
        if ev.lead_id not in lead_ids:
            continue
        new = (ev.notes or "").split("->")[-1].strip()
        std = to_standard(new)
        if is_won(std):
            conversions_week += 1
        elif is_lost(std):
            lost_week += 1

    assigned_week = sum(1 for l in leads if _as_date(l.created_date) and start <= _as_date(l.created_date) <= end)

    open_total = sum(n for st, n in statuses.items() if is_open(st))
    won_total = sum(n for st, n in statuses.items() if is_won(st))
    lost_total = sum(n for st, n in statuses.items() if is_lost(st))

    actionable = pending + overdue
    completion = round(agg["followups"] / (agg["followups"] + actionable) * 100, 1) if (agg["followups"] + actionable) else 0.0
    engagement_pct = round(len(contacted) / len(leads) * 100, 1) if leads else 0.0
    conv_pct = round(won_total / len(leads) * 100, 1) if leads else 0.0

    return {
        "assigned_week": assigned_week,
        "contacted_week": len(contacted),
        "calls": agg["calls"], "emails": agg["emails"], "whatsapp": agg["whatsapp"],
        "meetings_done": agg["meetings"], "notes_added": agg["notes"],
        "followups_completed": agg["followups"],
        "pending_followups": pending, "overdue_followups": overdue,
        "interested": statuses.get("Interested", 0),
        "negotiation": statuses.get("Negotiation", 0),
        "meetings_scheduled": statuses.get("Meeting Scheduled", 0),
        "quotations_sent": statuses.get("Quotation Sent", 0),
        "converted_total": won_total, "lost_total": lost_total, "open_total": open_total,
        "conversions_week": conversions_week, "lost_week": lost_week,
        "hot": bands.get("HOT", 0), "warm": bands.get("WARM", 0),
        "nurture": bands.get("NURTURE", 0), "cold": bands.get("COLD", 0),
        "conversion_pct": conv_pct, "task_completion_pct": completion, "engagement_pct": engagement_pct,
        "total_leads": len(leads),
    }


def overview_with_trend(session: Session, user: dict[str, Any], start: date, end: date) -> dict[str, Any]:
    """Weekly overview plus deltas vs the previous week."""
    cur = weekly_overview(session, user, start, end)
    p_start, p_end = start - timedelta(days=7), end - timedelta(days=7)
    prev = weekly_overview(session, user, p_start, p_end)
    trend_keys = ["calls", "emails", "whatsapp", "followups_completed", "contacted_week",
                  "conversions_week", "pending_followups", "overdue_followups", "meetings_done"]
    deltas = {}
    for k in trend_keys:
        c, p = cur.get(k, 0), prev.get(k, 0)
        if p == 0:
            pct = 100.0 if c > 0 else 0.0
        else:
            pct = round((c - p) / p * 100, 0)
        deltas[k] = {"current": c, "previous": p, "pct": pct, "dir": "up" if c > p else "down" if c < p else "flat"}
    return {"current": cur, "previous": prev, "deltas": deltas}


# --------------------------------------------------------------------------- #
# Section 2 — Salesperson performance
# --------------------------------------------------------------------------- #
def salesperson_performance(session: Session, start: date, end: date) -> list[dict[str, Any]]:
    leads = session.scalars(select(Lead).where(Lead.deleted_at.is_(None))).all()
    # Group case/space-insensitively so 'Rahul' and 'RAHUL' are one person, not two
    # leaderboard rows.
    by_person_leads, owner_display = _group_by_owner(leads)
    lead_ids = {l.lead_id for l in leads}
    acts = _collect_week_activity(session, lead_ids, start, end)

    today = biz_today()
    fu_next = _latest_followup_map(session)

    rows = []
    for key, pleads in by_person_leads.items():
        person = owner_display.get(key, key)
        pls = {l.lead_id for l in pleads}
        worked = set()
        agg = Counter()
        for lid in pls:
            if lid in acts:
                c = _classify_activity_counts(acts[lid])
                if c["total"]:
                    worked.add(lid)
                for k, v in c.items():
                    agg[k] += v
        overdue = sum(1 for lid in pls if _as_date(fu_next.get(lid)) and _as_date(fu_next.get(lid)) < today)
        statuses = Counter(to_standard(l.status) for l in pleads)
        assigned = len(pleads)
        ignored = assigned - len(worked)
        completed = agg["followups"] + agg["calls"] + agg["whatsapp"] + agg["emails"]
        completion = round(len(worked) / assigned * 100, 1) if assigned else 0.0
        # Composite scores (transparent)
        productivity = min(100, completed * 5)
        followup_quality = round(min(100, (agg["notes"] + agg["followups"]) / max(len(worked), 1) * 25), 1)
        handling = round((completion * 0.5) + (min(100, productivity) * 0.3) + (max(0, 100 - overdue * 10) * 0.2), 1)
        rows.append({
            "salesperson": person, "assigned": assigned, "worked": len(worked), "ignored": ignored,
            "calls": agg["calls"], "emails": agg["emails"], "whatsapp": agg["whatsapp"],
            "notes": agg["notes"], "followups": agg["followups"], "meetings": agg["meetings"],
            "overdue": overdue, "negotiation": statuses.get("Negotiation", 0),
            "meetings_scheduled": statuses.get("Meeting Scheduled", 0),
            "converted": sum(n for st, n in statuses.items() if is_won(st)),
            "lost": sum(n for st, n in statuses.items() if is_lost(st)),
            "completion_pct": completion, "followup_quality": followup_quality,
            "productivity": productivity, "handling_score": handling,
        })
    rows.sort(key=lambda r: (r["handling_score"], r["worked"], r["calls"]), reverse=True)
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    return rows


# --------------------------------------------------------------------------- #
# Section 3 — Weekly company activity table
# --------------------------------------------------------------------------- #
def company_activity(session: Session, user: dict[str, Any], start: date, end: date, only_worked: bool = True) -> list[dict[str, Any]]:
    leads = session.scalars(select(Lead).where(_scope(user))).all()
    lead_ids = {l.lead_id for l in leads}
    acts = _collect_week_activity(session, lead_ids, start, end)
    fu_next = _latest_followup_map(session, _scope(user))
    today = biz_today()

    rows = []
    for l in leads:
        items = acts.get(l.lead_id, [])
        if only_worked and not items:
            continue
        c = _classify_activity_counts(items)
        std = to_standard(l.status)
        score = float(l.lead_score or 0)
        band = band_for_score(score)
        # Previous status from latest status_change this week
        prev_status = "—"
        for a in reversed(items):
            if a["type"] == "status_change" and "->" in (a["text"] or ""):
                prev_status = to_standard(a["text"].split("->")[0].strip())
                break
        movement = "No change" if prev_status in ("—", std) else f"{prev_status} → {std}"
        last_activity = max((a["when"] for a in items), default=None)
        next_fu = _as_date(fu_next.get(l.lead_id))
        responded = any(a.get("source") == "engagement" and (a["type"] or "") in ("reply", "inbound") for a in items)
        # Risk + probability
        if std in ("Negotiation", "Meeting Scheduled", "Quotation Sent"):
            probability = min(95, int(score) + 20)
        else:
            probability = min(90, int(score))
        overdue = next_fu is not None and next_fu < today
        if not is_open(std):
            risk = "Closed"
        elif overdue and score < 50:
            risk = "High"
        elif overdue or score < 40:
            risk = "Medium"
        else:
            risk = "Low"
        rows.append({
            "company": l.company_name, "salesperson": l.assigned_to or "Unassigned",
            "score": score, "band": band, "date_assigned": _as_date(l.created_date),
            "work_done": f"{c['calls']}C/{c['whatsapp']}W/{c['emails']}E/{c['followups']}F",
            "contact_attempts": c["total"], "calls": c["calls"], "emails": c["emails"], "whatsapp": c["whatsapp"],
            "followups": c["followups"], "current_status": std, "previous_status": prev_status,
            "status_movement": movement, "stage": std,
            "response": "Yes" if responded else "—",
            "meeting": "Yes" if std == "Meeting Scheduled" or c["meetings"] else "No",
            "quotation_status": l.quotation_status or ("Sent" if std == "Quotation Sent" else "—"),
            "negotiation": "Yes" if std == "Negotiation" else "No",
            "last_activity": _as_date(last_activity), "next_followup": next_fu,
            "priority": l.priority_level or "MEDIUM",
            "notes_summary": (str(l.remarks or "")[:120]),
            "risk": risk, "probability": f"{probability}%", "lead_id": l.lead_id,
        })
    rows.sort(key=lambda r: r["score"], reverse=True)
    return rows


# --------------------------------------------------------------------------- #
# Section 4 — Company timeline
# --------------------------------------------------------------------------- #
def company_timeline(session: Session, lead_id: str, start: date, end: date) -> list[dict[str, Any]]:
    acts = _collect_week_activity(session, {lead_id}, start, end).get(lead_id, [])
    out = []
    for a in acts:
        when = a["when"]
        out.append({
            "day": when.strftime("%A") if when else "",
            "time": when.strftime("%Y-%m-%d %H:%M") if when else "",
            "type": a["type"], "source": a["source"], "user": a["user"] or "—", "detail": a["text"] or "",
        })
    return out


# --------------------------------------------------------------------------- #
# Section 5 — Lost opportunity analysis
# --------------------------------------------------------------------------- #
def lost_analysis(session: Session, user: dict[str, Any],
                  start: date | None = None, end: date | None = None) -> dict[str, Any]:
    """Loss analysis. When start/end are given, only leads that transitioned to a
    Lost status WITHIN that week (via a status_change event) are included, so the
    figures match the selected week instead of all-time. Without a window it falls
    back to all currently-lost leads in scope.
    """
    leads = {l.lead_id: l for l in session.scalars(select(Lead).where(_scope(user))).all()}
    scoped_ids = set(leads)
    _, owner_display = _group_by_owner(list(leads.values()))

    if start is not None and end is not None:
        # Leads that became Lost this week, from status_change events in the window.
        s, e = _dt_start(start), _dt_end(end)
        lost_ids: list[str] = []
        seen: set[str] = set()
        for ev in session.scalars(select(EngagementEvent).where(
            EngagementEvent.event_type == "status_change",
            EngagementEvent.occurred_at >= s, EngagementEvent.occurred_at <= e,
        )):
            if ev.lead_id not in scoped_ids or ev.lead_id in seen:
                continue
            new = (ev.notes or "").split("->")[-1].strip()
            if is_lost(to_standard(new)):
                lost_ids.append(ev.lead_id)
                seen.add(ev.lead_id)
        target = [leads[lid] for lid in lost_ids]
        scope_label = "week"
    else:
        target = [l for l in leads.values() if is_lost(to_standard(l.status))]
        scope_label = "all"

    reasons = Counter()
    by_person = defaultdict(Counter)
    by_country = defaultdict(Counter)
    lost_rows = []
    for l in target:
        text = " ".join(str(x or "") for x in (l.remarks, l.procurement_remarks, l.internal_notes)).lower()
        reason = l.lost_reason or "Unspecified"
        if reason == "Unspecified":
            for label, kws in _LOSS_PATTERNS:
                if any(k in text for k in kws):
                    reason = label
                    break
        owner = owner_display.get((l.assigned_to or "Unassigned").strip().lower(), l.assigned_to or "Unassigned")
        reasons[reason] += 1
        by_person[owner][reason] += 1
        by_country[(l.country or "Unknown").upper()][reason] += 1
        lost_rows.append({"company": l.company_name, "salesperson": owner,
                          "country": l.country or "Unknown", "reason": reason, "notes": str(l.remarks or "")[:120]})
    return {
        "reasons": dict(reasons.most_common()),
        "by_person": {p: dict(c) for p, c in by_person.items()},
        "by_country": {c: dict(v) for c, v in by_country.items()},
        "rows": lost_rows, "total_lost": len(lost_rows), "scope": scope_label,
    }


# --------------------------------------------------------------------------- #
# Section 7 — Management insights (auto-generated)
# --------------------------------------------------------------------------- #
def management_insights(session: Session, user: dict[str, Any], start: date, end: date) -> list[str]:
    insights: list[str] = []
    trend = overview_with_trend(session, user, start, end)
    d = trend["deltas"]
    cur = trend["current"]

    if d["calls"]["pct"]:
        arrow = "↑" if d["calls"]["dir"] == "up" else "↓"
        insights.append(f"Calls {arrow} {abs(d['calls']['pct']):.0f}% vs last week ({d['calls']['previous']} → {d['calls']['current']}).")
    if d["conversions_week"]["current"] or d["conversions_week"]["previous"]:
        arrow = "↑" if d["conversions_week"]["dir"] == "up" else "↓"
        insights.append(f"Conversions {arrow} {abs(d['conversions_week']['pct']):.0f}% this week ({d['conversions_week']['current']}).")
    if d["overdue_followups"]["dir"] == "down":
        insights.append(f"Overdue follow-ups reduced by {abs(d['overdue_followups']['pct']):.0f}% — good recovery.")
    elif d["overdue_followups"]["current"] > d["overdue_followups"]["previous"]:
        insights.append(f"Overdue follow-ups rising ({d['overdue_followups']['current']}) — needs attention.")

    perf = salesperson_performance(session, start, end)
    real = [p for p in perf if p["salesperson"] != "Unassigned"]
    if real:
        top = real[0]
        insights.append(f"Top performer: {top['salesperson']} (handling score {top['handling_score']}, {top['worked']} companies worked).")
        worst = min(real, key=lambda p: p["handling_score"])
        if worst["overdue"] >= 5:
            insights.append(f"{worst['salesperson']} has {worst['overdue']} overdue follow-ups — highest delay risk.")
        ignored = max(real, key=lambda p: p["ignored"])
        if ignored["ignored"] > 0:
            insights.append(f"{ignored['salesperson']} left {ignored['ignored']} assigned companies untouched this week.")

    # Country performance (open + won mix)
    leads = session.scalars(select(Lead).where(_scope(user))).all()
    country_open = Counter()
    country_won = Counter()
    for l in leads:
        std = to_standard(l.status)
        country = (l.country or "Unknown").upper()
        if is_won(std):
            country_won[country] += 1
        if is_open(std):
            country_open[country] += 1
    if country_won:
        best_country = country_won.most_common(1)[0]
        insights.append(f"{best_country[0].title()} leads converted best ({best_country[1]} won).")
    if cur["negotiation"]:
        insights.append(f"{cur['negotiation']} leads in active negotiation — prioritise to close.")
    if cur["nurture"] and cur["overdue_followups"]:
        insights.append("Nurture leads need faster follow-up cadence to avoid going cold.")
    if not insights:
        insights.append("Not enough weekly activity logged yet — insights sharpen as the team records calls, follow-ups, and status changes.")
    return insights


# --------------------------------------------------------------------------- #
# Section 8 — Next week pipeline
# --------------------------------------------------------------------------- #
def next_week_pipeline(session: Session, user: dict[str, Any]) -> dict[str, list[dict]]:
    leads = session.scalars(select(Lead).where(_scope(user))).all()
    today = biz_today()
    fu_next = _latest_followup_map(session, _scope(user))
    buckets = {"hot_followup": [], "negotiation": [], "interested": [], "pending_quotation": [], "overdue": [], "high_nurture": []}
    for l in leads:
        std = to_standard(l.status)
        if not is_open(std):
            continue
        score = float(l.lead_score or 0)
        band = band_for_score(score)
        row = {"company": l.company_name, "salesperson": l.assigned_to or "Unassigned",
               "score": score, "band": band, "status": std, "next_followup": _as_date(fu_next.get(l.lead_id)),
               "lead_id": l.lead_id}
        nd = _as_date(fu_next.get(l.lead_id))
        if nd and nd < today:
            buckets["overdue"].append(row)
        if band in ("HOT", "WARM"):
            buckets["hot_followup"].append(row)
        if std == "Negotiation":
            buckets["negotiation"].append(row)
        elif std == "Interested":
            buckets["interested"].append(row)
        elif std == "Quotation Sent":
            buckets["pending_quotation"].append(row)
        elif std == "Nurturing" and score >= 45:
            buckets["high_nurture"].append(row)
    for k in buckets:
        buckets[k].sort(key=lambda r: r["score"], reverse=True)
    return buckets
