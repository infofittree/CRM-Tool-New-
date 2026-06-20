"""CRM service layer used by Streamlit pages and future APIs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

import pandas as pd
from rapidfuzz import fuzz
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.security import hash_password
from database.crud import ActivityLogCRUD, FollowUpCRUD, LeadCRUD
from database.models import ALLOWED_STATUSES, EngagementEvent, Lead, LeadSequence, PRIORITY_LEVELS, User
from modules import dashboard_queries
from modules.dropdown_config import option_list
from modules.validation_engine import EMAIL_PATTERN, ValidationEngine
from modules.clock import today as biz_today


LEAD_SOURCES = option_list("lead_sources")
CONTINENTS = option_list("continents")
MODES = option_list("modes")
FOLLOWUP_STAGES = option_list("followup_stages")
QUOTATION_STATUSES = option_list("quotation_statuses")
BUYER_TAGS = option_list("buyer_tags")
PROBABILITIES = option_list("probabilities")
COUNTRIES = [
    "INDIA",
    "UNITED STATES",
    "UNITED KINGDOM",
    "UNITED ARAB EMIRATES",
    "KENYA",
    "SAUDI ARABIA",
    "SOUTH AFRICA",
    "GERMANY",
    "FRANCE",
    "CANADA",
    "AUSTRALIA",
    "OTHER",
]


@dataclass
class SaveResult:
    """Result returned after data-entry save attempts."""

    ok: bool
    message: str
    lead_id: str | None = None
    duplicates: list[dict[str, Any]] | None = None


class CRMService:
    """Shared CRM operations for dashboard, forms, analytics, and exports."""

    def __init__(self, session: Session, logger=None) -> None:
        self.session = session
        self.logger = logger
        self.leads = LeadCRUD()
        self.followups = FollowUpCRUD()
        self.activity = ActivityLogCRUD()
        self.validator = ValidationEngine()

    def generate_lead_id(self, year: int | None = None) -> str:
        """Generate a collision-proof lead ID.

        After a bulk import the sequence counter can lag behind the real max
        lead number, causing duplicate-PK failures. We reconcile the counter with
        the actual highest existing FT-YYYY-NNNN before issuing the next id.
        """
        import re
        year = year or biz_today().year
        prefix = f"FT-{year}-"
        max_existing = 0
        for lid in self.session.scalars(select(Lead.lead_id).where(Lead.lead_id.like(prefix + "%"))):
            m = re.match(rf"FT-{year}-(\d+)$", str(lid))
            if m:
                max_existing = max(max_existing, int(m.group(1)))

        sequence = self.session.get(LeadSequence, year)
        if sequence is None:
            sequence = LeadSequence(year=year, last_number=max_existing)
            self.session.add(sequence)
            self.session.flush()
        sequence.last_number = max(sequence.last_number, max_existing) + 1
        return f"{prefix}{sequence.last_number:04d}"

    def get_salespersons(self) -> list[str]:
        """Return active salesperson names from users and existing assignments."""
        user_names = self.session.scalars(
            select(User.full_name).where(User.role.in_(["Salesperson", "Manager", "Admin"]), User.is_active.is_(True))
        ).all()
        assigned = self.session.scalars(select(Lead.assigned_to).where(Lead.assigned_to.is_not(None)).distinct()).all()
        values = sorted({name for name in [*user_names, *assigned] if name})
        return values or ["Unassigned"]

    def dashboard_metrics(self, user: dict) -> dict[str, Any]:
        """Compute dashboard KPIs scoped by role."""
        total = dashboard_queries.get_total_leads(self.session, user)
        active = dashboard_queries.get_active_leads(self.session, user)
        nurturing = dashboard_queries.get_nurturing_leads(self.session, user)
        converted = dashboard_queries.get_converted_leads(self.session, user)
        due_today = dashboard_queries.get_due_today_followups(self.session, user)
        overdue = dashboard_queries.get_overdue_followups(self.session, user)
        return {
            "total": total,
            "active": active,
            "nurturing": nurturing,
            "due_today": due_today,
            "overdue": overdue,
            "converted": converted,
            "conversion_rate": dashboard_queries.get_conversion_rate(self.session, user),
        }

    def leads_dataframe(self, user: dict, limit: int = 500) -> pd.DataFrame:
        """Return scoped leads as a dataframe."""
        return dashboard_queries.get_leads_dataframe(self.session, user, limit=limit)

    def followups_dataframe(self, user: dict, horizon_days: int = 30) -> pd.DataFrame:
        """Return follow-ups joined to lead context."""
        return dashboard_queries.get_followups_dataframe(self.session, user, horizon_days=horizon_days)

    def save_lead_from_entry(self, payload: dict[str, Any], user: dict, force: bool = False) -> SaveResult:
        """Validate, de-duplicate, insert lead, create first follow-up, and audit."""
        cleaned = self._clean_entry_payload(payload)
        validation_errors = self._validate_entry(cleaned)
        if validation_errors:
            return SaveResult(False, "; ".join(validation_errors))

        duplicates = self.find_duplicates(cleaned)
        if duplicates and not force:
            return SaveResult(False, "Possible duplicate detected.", duplicates=duplicates)

        try:
            cleaned["lead_id"] = cleaned.get("lead_id") or self.generate_lead_id()
            cleaned["created_date"] = cleaned.get("created_date") or biz_today()
            cleaned["lead_score"] = cleaned.get("lead_score") or self._initial_lead_score(cleaned)
            lead = self.leads.create_lead(self.session, cleaned)

            if cleaned.get("last_discussion") or cleaned.get("next_action") or cleaned.get("next_follow_up"):
                self.followups.add_followup(
                    self.session,
                    {
                        "lead_id": lead.lead_id,
                        "followup_date": biz_today(),
                        "discussion": cleaned.get("last_discussion"),
                        "next_action": cleaned.get("next_action"),
                        "next_followup": cleaned.get("next_follow_up"),
                        "updated_by": user["full_name"],
                    },
                )
            self.activity.log_activity(self.session, "CREATE_LEAD_FROM_DATA_ENTRY", user["full_name"], lead.lead_id)
            return SaveResult(True, "Lead saved successfully.", lead_id=lead.lead_id)
        except Exception as exc:  # Phase 7: never fail silently
            import traceback as _tb
            self.log_error("save_lead_from_entry", str(exc), user, _tb.format_exc())
            return SaveResult(False, f"Save failed: {exc}")

    def add_quick_followup(self, lead_id: str, payload: dict[str, Any], user: dict) -> None:
        """Add follow-up, update lead state, and audit."""
        self.followups.add_followup(
            self.session,
            {
                "lead_id": lead_id,
                "followup_date": biz_today(),
                "discussion": payload.get("discussion"),
                "next_action": payload.get("next_action"),
                "next_followup": payload.get("next_followup"),
                "mode": payload.get("mode"),
                "updated_by": user["full_name"],
            },
        )
        lead = self.session.get(Lead, lead_id)
        if lead:
            lead.last_contact_date = biz_today()
            if payload.get("next_action"):
                lead.next_action_plan = payload["next_action"]
            new_status = payload.get("status")
            if new_status and new_status != lead.status:
                # Record status movement for weekly review / history (Section 12)
                self.session.add(
                    EngagementEvent(
                        lead_id=lead_id, user_name=user["full_name"], event_type="status_change",
                        notes=f"{lead.status} -> {new_status}",
                    )
                )
                lead.status = new_status
                # Lost reason capture (mandatory at UI layer)
                if new_status == "Lost" and payload.get("lost_reason"):
                    lead.lost_reason = payload["lost_reason"]
            # Recompute score live after status change
            try:
                from modules.lead_scoring import score_lead
                lead.lead_score = score_lead({c.name: getattr(lead, c.name) for c in Lead.__table__.columns})[0]
            except Exception:
                pass
        # Record an engagement event so call/WhatsApp/email history accrues
        mode = str(payload.get("mode") or "").strip().lower()
        channel_map = {"calling": "call", "call": "call", "whatsapp": "whatsapp", "email": "email", "meeting": "meeting"}
        self.session.add(
            EngagementEvent(
                lead_id=lead_id,
                user_name=user["full_name"],
                event_type=channel_map.get(mode, "followup"),
                channel=mode or None,
                direction="outbound",
                notes=payload.get("discussion") or payload.get("next_action"),
            )
        )
        self.activity.log_activity(self.session, "ADD_QUICK_FOLLOWUP", user["full_name"], lead_id)

    def get_tasks(self, user: dict, upcoming_days: int = 7, max_today: int = 30) -> dict:
        """Return the live derived task queue for a user (today/overdue/upcoming)."""
        from modules import task_engine
        return task_engine.generate_tasks(self.session, user, upcoming_days=upcoming_days, max_today=max_today)

    def update_lead_full(self, lead_id: str, payload: dict[str, Any], user: dict) -> None:
        """Full lead update from Lead Detail — category + buyer level + follow-up,
        with category-change tracking in the activity timeline."""
        lead = self.session.get(Lead, lead_id)
        if lead:
            # Lead Category change tracking (Patch 1)
            new_cat = payload.get("lead_category")
            if new_cat and new_cat not in ("— select —",) and new_cat != (lead.lead_category or ""):
                old_cat = lead.lead_category or "—"
                self.session.add(EngagementEvent(
                    lead_id=lead_id, user_name=user["full_name"], event_type="category_change",
                    notes=f"Lead Category changed from {old_cat} → {new_cat}",
                ))
                self.activity.log_activity(
                    self.session, "CATEGORY_CHANGE", user["full_name"], lead_id,
                    remarks=f"{old_cat} → {new_cat}",
                )
                lead.lead_category = new_cat
            # Alibaba buyer level
            if "buyer_tag" in payload:
                lead.buyer_tag = payload.get("buyer_tag")
            if payload.get("lost_reason"):
                lead.lost_reason = payload["lost_reason"]
        # Reuse the quick-followup pipeline for status/followup/notes/score
        self.add_quick_followup(lead_id, payload, user)

    def reschedule_followup(self, lead_id: str, new_date, user: dict, note: str | None = None) -> None:
        """Reschedule a lead's next follow-up to a new date and log it."""
        self.followups.add_followup(
            self.session,
            {
                "lead_id": lead_id,
                "followup_date": biz_today(),
                "discussion": note or "Rescheduled",
                "next_action": "Follow up",
                "next_followup": new_date,
                "updated_by": user["full_name"],
            },
        )
        self.session.add(
            EngagementEvent(lead_id=lead_id, user_name=user["full_name"], event_type="reschedule", notes=note)
        )
        self.activity.log_activity(self.session, "RESCHEDULE_FOLLOWUP", user["full_name"], lead_id)

    def append_note(self, lead_id: str, note: str, user: dict) -> None:
        """Append a timestamped note to a lead and log an engagement event."""
        lead = self.session.get(Lead, lead_id)
        if lead:
            stamp = biz_today().isoformat()
            existing = (lead.remarks or "").strip()
            lead.remarks = f"{existing}\n[{stamp} {user['full_name']}] {note}".strip()
        self.session.add(
            EngagementEvent(lead_id=lead_id, user_name=user["full_name"], event_type="note", notes=note)
        )
        self.activity.log_activity(self.session, "ADD_NOTE", user["full_name"], lead_id)

    def bulk_import_dataframe(self, df: pd.DataFrame, user: dict) -> dict[str, int]:
        """Import valid rows from uploaded Excel/CSV data."""
        summary = {"inserted": 0, "duplicates_skipped": 0, "invalid_rows": 0, "failed_rows": 0}
        for _, row in df.fillna("").iterrows():
            payload = {str(key).strip().lower().replace(" ", "_"): value for key, value in row.to_dict().items()}
            result = self.save_lead_from_entry(payload, user, force=False)
            if result.ok:
                summary["inserted"] += 1
            elif result.duplicates:
                summary["duplicates_skipped"] += 1
            elif "required" in result.message or "invalid" in result.message.lower():
                summary["invalid_rows"] += 1
            else:
                summary["failed_rows"] += 1
        return summary

    def delete_lead_logged(self, lead_id: str, user: dict, reason: str | None = None) -> bool:
        """Phase 3: snapshot the lead to deleted_leads, then soft-delete it. No data loss."""
        import json
        from datetime import datetime
        from database.models import DeletedLead
        lead = self.session.get(Lead, lead_id)
        if lead is None:
            return False
        snapshot = {c.name: getattr(lead, c.name) for c in Lead.__table__.columns}
        self.session.add(DeletedLead(
            lead_id=lead_id,
            company_name=lead.company_name,
            contact_name=lead.contact_person,
            assigned_to=lead.assigned_to,
            deleted_by=user["full_name"],
            reason=reason,
            snapshot=json.dumps(snapshot, default=str),
        ))
        lead.deleted_at = datetime.utcnow()  # soft delete — row preserved
        self.activity.log_activity(self.session, "DELETE_LEAD", user["full_name"], lead_id, remarks=reason)
        return True

    # Fields the separate Edit-Lead form may change (4.1).
    EDITABLE_FIELDS = (
        "contact_person", "company_name", "email", "phone", "country", "continent",
        "industry", "lead_source", "status", "remarks", "website", "address",
    )

    def edit_lead_fields(self, lead_id: str, new_values: dict[str, Any], user: dict) -> list[str]:
        """4.1: update lead fields with a before/after audit trail. Returns change list."""
        from modules.geo import normalize_country, country_continent, normalize_source
        lead = self.session.get(Lead, lead_id)
        if lead is None:
            return []
        # Normalize geo/source so derived data stays consistent
        if new_values.get("country"):
            new_values["country"] = normalize_country(new_values["country"])
            new_values["continent"] = country_continent(new_values["country"]) or new_values.get("continent")
        if new_values.get("lead_source"):
            new_values["lead_source"] = normalize_source(new_values["lead_source"])
        if new_values.get("company_name") is not None:
            new_values["company_name"] = str(new_values["company_name"]).strip().upper() or None

        changes: list[str] = []
        for field in self.EDITABLE_FIELDS:
            if field not in new_values:
                continue
            old = getattr(lead, field, None)
            new = new_values[field]
            new = (new.strip() if isinstance(new, str) else new) or None
            if str(old or "") != str(new or ""):
                setattr(lead, field, new)
                changes.append(f"{field}: '{old or '—'}' → '{new or '—'}'")
                self.session.add(EngagementEvent(
                    lead_id=lead_id, user_name=user["full_name"], event_type="field_edit",
                    notes=f"{field}: {old or '—'} -> {new or '—'}",
                ))
        if changes:
            # recompute score if status changed
            if any(c.startswith("status:") for c in changes):
                from modules.lead_scoring import score_lead
                lead.lead_score = score_lead({c.name: getattr(lead, c.name) for c in Lead.__table__.columns})[0]
            self.activity.log_activity(
                self.session, "EDIT_LEAD", user["full_name"], lead_id, remarks="; ".join(changes)[:1000],
            )
        return changes

    def transfer_lead(self, lead_id: str, new_owner: str, user: dict, reason: str | None = None) -> bool:
        """Phase 4: reassign a lead to another salesperson and record the transfer."""
        from database.models import LeadTransfer
        lead = self.session.get(Lead, lead_id)
        if lead is None or not new_owner:
            return False
        old_owner = lead.assigned_to
        if old_owner == new_owner:
            return False
        self.session.add(LeadTransfer(
            lead_id=lead_id, transferred_from=old_owner, transferred_to=new_owner,
            reason=reason, transferred_by=user["full_name"],
        ))
        lead.assigned_to = new_owner
        self.activity.log_activity(
            self.session, "TRANSFER_LEAD", user["full_name"], lead_id,
            remarks=f"{old_owner or '—'} -> {new_owner}" + (f" ({reason})" if reason else ""),
        )
        return True

    def log_error(self, module: str, error: str, user: dict | None = None, tb: str | None = None) -> None:
        """Phase 7: persist an error so failures are never silent."""
        try:
            from database.models import ErrorLog
            self.session.add(ErrorLog(
                module=module, error=str(error)[:2000],
                user_name=(user or {}).get("full_name"), traceback=(tb or "")[:5000],
            ))
        except Exception:
            pass  # logging must never raise

    def find_duplicates(self, payload: dict[str, Any], threshold: int = 88) -> list[dict[str, Any]]:
        """Find likely existing duplicates by email, phone, and fuzzy company name."""
        company = str(payload.get("company_name") or "")
        email = str(payload.get("email") or "").lower()
        phone = str(payload.get("phone") or "")
        stmt = select(Lead).where(Lead.deleted_at.is_(None))
        duplicates = []
        for lead in self.session.scalars(stmt):
            reasons = []
            score = fuzz.token_set_ratio(company, lead.company_name or "") if company and lead.company_name else 0
            if score >= threshold:
                reasons.append(f"company similarity {score}")
            if email and lead.email and email == lead.email.lower():
                reasons.append("same email")
                score = max(score, 100)
            if phone and lead.phone and phone == lead.phone:
                reasons.append("same phone")
                score = max(score, 100)
            if reasons:
                duplicates.append({"lead_id": lead.lead_id, "company_name": lead.company_name, "similarity": score, "reasons": ", ".join(reasons)})
        return sorted(duplicates, key=lambda item: item["similarity"], reverse=True)[:5]

    def create_user(self, username: str, password: str, full_name: str, role: str) -> None:
        """Create a CRM user."""
        self.session.add(User(username=username, password_hash=hash_password(password), full_name=full_name, role=role, is_active=True))

    def user_workload(self, full_name: str) -> dict[str, int]:
        """Count active leads (and open follow-ups) owned by a user — for delete preview."""
        from sqlalchemy import func
        leads_n = self.session.scalar(
            select(func.count()).select_from(Lead).where(
                func.lower(func.trim(Lead.assigned_to)) == (full_name or "").strip().lower(),
                Lead.deleted_at.is_(None),
            )
        ) or 0
        return {"leads": int(leads_n)}

    def delete_user(self, username: str, actor: dict, mode: str = "transfer",
                    transfer_to: str | None = None) -> tuple[bool, str]:
        """Delete a user (soft) after reassigning or unassigning their leads.

        mode='transfer' -> move their leads to transfer_to; mode='unassign' -> clear owner.
        Returns (ok, message). Guards: can't delete self or the last active admin.
        """
        from sqlalchemy import func
        target = self.session.scalar(select(User).where(User.username == username))
        if target is None:
            return False, "User not found."
        if target.username == actor.get("username"):
            return False, "You cannot delete your own account."
        if target.role == "Admin":
            admin_count = self.session.scalar(
                select(func.count()).select_from(User).where(User.role == "Admin", User.is_active.is_(True))
            ) or 0
            if admin_count <= 1:
                return False, "Cannot delete the last active Admin."

        owner = target.full_name or target.username
        leads = self.session.scalars(
            select(Lead).where(func.lower(func.trim(Lead.assigned_to)) == owner.strip().lower(), Lead.deleted_at.is_(None))
        ).all()
        if mode == "transfer":
            if not transfer_to:
                return False, "Choose a user to transfer leads to."
            for l in leads:
                l.assigned_to = transfer_to
        else:  # unassign
            for l in leads:
                l.assigned_to = None

        target.is_active = False
        from datetime import datetime
        target.deleted_at = datetime.utcnow()
        self.activity.log_activity(
            self.session, "DELETE_USER", actor["full_name"], None,
            remarks=f"Deleted user '{username}' ({len(leads)} leads {mode}"
                    + (f"->{transfer_to}" if mode == 'transfer' else " unassigned") + ")",
        )
        return True, f"User '{username}' deleted; {len(leads)} leads {mode}{(' to ' + transfer_to) if mode=='transfer' else 'ed'}."

    _MAX_FOLLOWUP_DAYS = 30
    _CANONICAL_STATUSES = {
        "Prospect", "Requirement Qualified", "Technical Discussion",
        "Quotation Sent", "Sample Sent", "Negotiation", "Trial Order",
        "Order Closed", "Nurturing", "Lost",
    }
    _LOST_REASONS = {
        "Price Too High", "Existing Supplier", "Product Not Available",
        "Price Issues", "Certification Concern", "Imported Locally", "Quality Concern",
        "Not Replying",
    }

    def _validate_entry(self, payload: dict[str, Any]) -> list[str]:
        from datetime import timedelta
        errors = []
        # Required core fields (company name, phone, and email are all OPTIONAL)
        for field in ("contact_person", "status", "assigned_to", "country"):
            if not payload.get(field):
                label = field.replace("_", " ").title()
                errors.append(f"{label} is required")
        # Status must be canonical
        status = payload.get("status", "")
        if status and status not in self._CANONICAL_STATUSES:
            errors.append(f"Invalid status '{status}'. Must be one of: {', '.join(sorted(self._CANONICAL_STATUSES))}")
        is_lost = status == "Lost"
        # Follow-up date + action plan are NOT required for Lost leads (Phase 5).
        if not is_lost:
            fu_date = payload.get("next_follow_up") or payload.get("follow_up_date")
            if not fu_date:
                errors.append("Follow-up date is mandatory — no lead can be saved without one.")
            else:
                try:
                    if isinstance(fu_date, str):
                        fu_date = date.fromisoformat(str(fu_date)[:10])
                    if hasattr(fu_date, 'date'):  # datetime → date
                        fu_date = fu_date.date()
                    days_ahead = (fu_date - biz_today()).days
                    if days_ahead > self._MAX_FOLLOWUP_DAYS:
                        errors.append(f"Follow-up date cannot exceed {self._MAX_FOLLOWUP_DAYS} days from today. Set a closer date.")
                    elif days_ahead < -180:
                        errors.append("Follow-up date appears too far in the past. Please enter today or a future date.")
                except (ValueError, TypeError, AttributeError):
                    errors.append("Follow-up date format is invalid.")
            # Next Action Plan — MANDATORY (except for Lost)
            if not str(payload.get("next_action_plan") or "").strip():
                errors.append("Next Action Plan is mandatory — explain what will be done on the follow-up.")
        # Lead Category — MANDATORY (A/B/C, manual decision, no auto-default)
        cat = str(payload.get("lead_category") or "").strip().upper()
        if not cat:
            errors.append("Lead Category (A/B/C) is mandatory.")
        elif cat not in {"A", "B", "C"}:
            errors.append("Lead Category must be A, B, or C.")
        # Lead Source — MANDATORY (dropdown only)
        if not str(payload.get("lead_source") or "").strip():
            errors.append("Lead Source is mandatory.")
        # Lost reason mandatory when status is Lost
        if status == "Lost" and not payload.get("lost_reason"):
            errors.append("Lost Reason is mandatory when marking a lead as Lost.")
        if payload.get("lost_reason") and payload["lost_reason"] not in self._LOST_REASONS:
            errors.append(f"Lost reason must be one of: {', '.join(self._LOST_REASONS)}")
        # Email format
        if payload.get("email") and not EMAIL_PATTERN.match(payload["email"]):
            errors.append("Invalid email format.")
        # Phone
        if payload.get("phone") and len("".join(ch for ch in payload["phone"] if ch.isdigit())) < 7:
            errors.append("Invalid phone format (min 7 digits).")
        return errors

    def _clean_entry_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        from modules.status_taxonomy import to_canonical
        from modules.geo import normalize_country, country_continent, normalize_source
        phone = self._clean_phone(payload.get("phone"))
        alternate = self._clean_phone(payload.get("alternate_number"))
        whatsapp = self._clean_phone(payload.get("whatsapp_number"))
        # Company name is optional (Phase 6): fall back to contact person so the
        # display/dedup stays meaningful and the NOT NULL column is satisfied.
        company = str(payload.get("company_name") or "").strip().upper()
        if not company:
            company = str(payload.get("contact_person") or "").strip().upper() or "—"
        clean_country = normalize_country(payload.get("country"))
        cleaned = {key: (value.strip() if isinstance(value, str) else value) for key, value in payload.items()}
        # Category: NO auto-default — must be set by the salesperson (mandatory)
        raw_cat = str(payload.get("lead_category") or "").strip().upper()
        cleaned.update(
            {
                "company_name": company,
                "phone": phone,
                "alternate_number": alternate,
                "whatsapp_number": whatsapp,
                "email": str(payload.get("email") or "").strip().lower() or None,
                "country": clean_country,
                "continent": country_continent(clean_country),  # auto-mapped
                "lead_source": normalize_source(payload.get("lead_source")) if payload.get("lead_source") else None,
                "status": to_canonical(payload.get("status") or "Prospect"),
                "priority_level": payload.get("priority_level") or "MEDIUM",
                "next_follow_up": payload.get("next_follow_up"),
                "lead_category": raw_cat or None,
                "buyer_engagement_frequency": payload.get("buyer_engagement_frequency") or "Medium",
                "next_action_plan": str(payload.get("next_action_plan") or "").strip() or None,
                "lost_reason": payload.get("lost_reason") if payload.get("status") == "Lost" else None,
            }
        )
        return cleaned

    @staticmethod
    def _initial_lead_score(payload: dict[str, Any]) -> float:
        from modules.lead_scoring import score_lead
        score, _, _ = score_lead(payload)
        return score

    def _lead_scope(self, user: dict):
        return dashboard_queries.lead_scope(user)

    @staticmethod
    def _lead_dict(lead: Lead) -> dict[str, Any]:
        return {column.name: getattr(lead, column.name) for column in Lead.__table__.columns}

    @staticmethod
    def _clean_phone(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        if text.endswith(".0") and text.replace(".0", "").isdigit():
            text = text[:-2]
        cleaned = "".join(ch for ch in text if ch.isdigit() or ch == "+")
        if cleaned.count("+") > 1:
            cleaned = "+" + cleaned.replace("+", "")
        if "+" in cleaned and not cleaned.startswith("+"):
            cleaned = cleaned.replace("+", "")
        return cleaned or None
