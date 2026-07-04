"""Reusable CRUD operations for CRM modules and future APIs."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Select, or_, select
from sqlalchemy.orm import Session

from database.models import ActivityLog, DuplicateReport, FollowUp, Lead
from modules.validation_engine import ValidationEngine


class LeadCRUD:
    """Lead CRUD operations with validation and pagination."""

    def __init__(self, validator: ValidationEngine | None = None) -> None:
        self.validator = validator or ValidationEngine()

    def create_lead(self, session: Session, payload: dict[str, Any]) -> Lead:
        """Create a lead after validation."""
        result = self.validator.validate_lead_payload(payload)
        if not result.is_valid:
            raise ValueError("; ".join(result.errors))
        lead = Lead(**self._clean_model_payload(Lead, payload))
        session.add(lead)
        return lead

    def update_lead(self, session: Session, lead_id: str, payload: dict[str, Any]) -> Lead:
        """Update an existing lead."""
        lead = self.get_lead_by_id(session, lead_id)
        if lead is None:
            raise LookupError(f"Lead not found: {lead_id}")
        for key, value in self._clean_model_payload(Lead, payload).items():
            if key != "lead_id":
                setattr(lead, key, value)
        return lead

    def delete_lead(self, session: Session, lead_id: str, soft_delete: bool = True) -> None:
        """Delete a lead, soft by default."""
        lead = self.get_lead_by_id(session, lead_id)
        if lead is None:
            raise LookupError(f"Lead not found: {lead_id}")
        if soft_delete:
            lead.deleted_at = datetime.utcnow()
        else:
            session.delete(lead)

    def get_lead_by_id(self, session: Session, lead_id: str) -> Lead | None:
        """Fetch one active lead by ID."""
        return session.get(Lead, lead_id)

    def get_all_leads(self, session: Session, page: int = 1, page_size: int = 100, include_deleted: bool = False) -> list[Lead]:
        """Fetch paginated leads."""
        stmt = select(Lead).order_by(Lead.updated_at.desc())
        if not include_deleted:
            stmt = stmt.where(Lead.deleted_at.is_(None))
        return list(session.scalars(self._paginate(stmt, page, page_size)))

    def search_leads(
        self,
        session: Session,
        query: str,
        page: int = 1,
        page_size: int = 100,
        include_deleted: bool = False,
    ) -> list[Lead]:
        """Search by company, contact, email, phone, country, or assignee."""
        pattern = f"%{query}%"
        stmt = select(Lead).where(
            or_(
                Lead.company_name.ilike(pattern),
                Lead.contact_person.ilike(pattern),
                Lead.email.ilike(pattern),
                Lead.phone.ilike(pattern),
                Lead.country.ilike(pattern),
                Lead.assigned_to.ilike(pattern),
            )
        )
        if not include_deleted:
            stmt = stmt.where(Lead.deleted_at.is_(None))
        return list(session.scalars(self._paginate(stmt.order_by(Lead.updated_at.desc()), page, page_size)))

    _COLUMN_CACHE: dict[str, list[dict]] = {}

    @classmethod
    def _clean_model_payload(cls, model: type, payload: dict[str, Any]) -> dict[str, Any]:
        cache_key = model.__tablename__
        if cache_key not in cls._COLUMN_CACHE:
            cls._COLUMN_CACHE[cache_key] = [
                {"name": col.name, "nullable": col.nullable, "default": col.default}
                for col in model.__table__.columns
            ]
        result: dict[str, Any] = {}
        for col in cls._COLUMN_CACHE[cache_key]:
            if col["name"] not in payload:
                continue
            value = payload[col["name"]]
            if value is None and not col["nullable"]:
                default = col["default"]
                if default is not None and callable(getattr(default, "arg", None)):
                    value = default.arg(None)
                elif default is not None and hasattr(default, "arg"):
                    value = default.arg
                else:
                    continue
            result[col["name"]] = value
        return result

    @staticmethod
    def _paginate(stmt: Select, page: int, page_size: int) -> Select:
        page = max(page, 1)
        page_size = min(max(page_size, 1), 500)
        return stmt.limit(page_size).offset((page - 1) * page_size)


class FollowUpCRUD:
    """Follow-up CRUD operations."""

    def __init__(self, validator: ValidationEngine | None = None) -> None:
        self.validator = validator or ValidationEngine()

    def add_followup(self, session: Session, payload: dict[str, Any]) -> FollowUp:
        """Create a follow-up row."""
        result = self.validator.validate_followup_payload(payload)
        if not result.is_valid:
            raise ValueError("; ".join(result.errors))
        followup = FollowUp(**LeadCRUD._clean_model_payload(FollowUp, payload))
        session.add(followup)
        session.flush()  # Generate auto-incremented followup_id
        return followup

    def get_followups(self, session: Session, lead_id: str) -> list[FollowUp]:
        """Fetch follow-ups for one lead."""
        stmt = select(FollowUp).where(FollowUp.lead_id == lead_id).order_by(FollowUp.followup_date.desc())
        return list(session.scalars(stmt))

    def update_followup(self, session: Session, followup_id: int, payload: dict[str, Any]) -> FollowUp:
        """Update one follow-up."""
        followup = session.get(FollowUp, followup_id)
        if followup is None:
            raise LookupError(f"Follow-up not found: {followup_id}")
        for key, value in LeadCRUD._clean_model_payload(FollowUp, payload).items():
            if key != "followup_id":
                setattr(followup, key, value)
        return followup


class ActivityLogCRUD:
    """Activity log operations."""

    def log_activity(
        self,
        session: Session,
        action: str,
        user_name: str | None = None,
        lead_id: str | None = None,
        remarks: str | None = None,
    ) -> ActivityLog:
        """Write an audit event."""
        log = ActivityLog(action=action, user_name=user_name, lead_id=lead_id, remarks=remarks)
        session.add(log)
        return log


class DuplicateReportCRUD:
    """Duplicate report operations."""

    def create_or_update_duplicate(
        self,
        session: Session,
        lead_1: str,
        lead_2: str,
        similarity_score: float,
        status: str = "PENDING",
    ) -> DuplicateReport:
        """Upsert one duplicate report pair."""
        left, right = sorted([lead_1, lead_2])
        stmt = select(DuplicateReport).where(DuplicateReport.lead_1 == left, DuplicateReport.lead_2 == right)
        report = session.scalar(stmt)
        if report is None:
            report = DuplicateReport(lead_1=left, lead_2=right, similarity_score=similarity_score, status=status)
            session.add(report)
        else:
            report.similarity_score = similarity_score
            report.status = status
        return report

