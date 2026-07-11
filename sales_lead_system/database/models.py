"""SQLAlchemy ORM models for the CRM database."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, deferred, mapped_column, relationship

from modules.dropdown_config import all_allowed_statuses


ALLOWED_STATUSES = all_allowed_statuses()

USER_ROLES = ("Admin", "Manager", "Salesperson", "Procurement")
PRIORITY_LEVELS = ("HIGH", "MEDIUM", "LOW")

INQUIRY_TYPES = ("PRICING", "AVAILABILITY", "PACKAGING", "DOCUMENTATION", "MOQ", "LEAD_TIME", "CUSTOM")
INQUIRY_PRIORITIES = ("LOW", "MEDIUM", "HIGH", "URGENT")
INQUIRY_STATUSES = ("OPEN", "EOD_COMMITTED", "PENDING_RESPONSE", "RESPONDED", "OVERDUE", "CLOSED")
INQUIRY_COMMITMENT_TYPES = ("ANSWER_NOW", "BY_EOD", "WILL_TAKE_TIME")


class Base(DeclarativeBase):
    """Reusable SQLAlchemy declarative base."""


class TimestampMixin:
    """Common timestamp fields for auditable tables."""

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


class SoftDeleteMixin:
    """Soft delete marker for future multi-user CRM workflows.

    `is_deleted` bool replaces `deleted_at IS NULL` checks for faster querying.
    Both columns coexist — `is_deleted` is the indexable flag, `deleted_at` preserves
    the timestamp for audit purposes. Backfilled by `ensure_phase6_schema()`.
    """

    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0", index=True)


class Lead(Base, TimestampMixin, SoftDeleteMixin):
    """Lead master record."""

    __tablename__ = "leads"
    __table_args__ = (
        Index("ix_leads_company_name", "company_name"),
        Index("ix_leads_status_assigned", "status", "assigned_to"),
        Index("ix_leads_priority", "priority_level"),
        Index("ix_leads_email", "email"),
        Index("ix_leads_phone", "phone"),
        Index("ix_leads_deleted_assigned", "deleted_at", "assigned_to"),
        Index("ix_leads_is_deleted_assigned", "is_deleted", "assigned_to"),
        Index("ix_leads_lead_id_prefix", "lead_id"),
    )

    lead_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    legacy_buyer_id: Mapped[str | None] = mapped_column(String(50), index=True)
    buyer_tag: Mapped[str | None] = mapped_column(String(20))
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    website: Mapped[str | None] = mapped_column(String(255))
    industry: Mapped[str | None] = mapped_column(String(120))
    city: Mapped[str | None] = mapped_column(String(120))
    contact_person: Mapped[str | None] = mapped_column(String(255))
    designation: Mapped[str | None] = mapped_column(String(120))
    phone: Mapped[str | None] = mapped_column(String(50))
    alternate_number: Mapped[str | None] = mapped_column(String(50))
    whatsapp_number: Mapped[str | None] = mapped_column(String(50))
    email: Mapped[str | None] = mapped_column(String(255))
    country: Mapped[str | None] = mapped_column(String(100))
    continent: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="Prospect", server_default="Prospect", index=True)
    assigned_to: Mapped[str | None] = mapped_column(String(100), index=True)
    transfer_to: Mapped[str | None] = mapped_column(String(100))
    lead_source: Mapped[str | None] = mapped_column(String(100))
    product_interest: Mapped[str | None] = mapped_column(String(255))
    probability: Mapped[str | None] = mapped_column(String(20))
    follow_up_stage: Mapped[str | None] = mapped_column(String(50))
    mode: Mapped[str | None] = mapped_column(String(50))
    quotation_status: Mapped[str | None] = mapped_column(String(50))
    moq_requirement: Mapped[str | None] = mapped_column(String(100))
    expected_quantity: Mapped[str | None] = mapped_column(String(100))
    budget_range: Mapped[str | None] = mapped_column(String(100))
    priority_level: Mapped[str] = mapped_column(String(20), nullable=False, default="MEDIUM", server_default="MEDIUM", index=True)
    remarks: Mapped[str | None] = deferred(mapped_column(Text))
    procurement_remarks: Mapped[str | None] = deferred(mapped_column(Text))
    internal_notes: Mapped[str | None] = deferred(mapped_column(Text))
    created_date: Mapped[date | None] = mapped_column(Date)
    lead_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    last_contact_date: Mapped[date | None] = mapped_column(Date)
    # Phase 3 — aligned with updated Google Sheet (2026-06-01)
    first_contact_date: Mapped[date | None] = mapped_column(Date)
    sheet_source: Mapped[str | None] = mapped_column(String(50))  # Buyer_Master | Alibaba
    # Phase 4 — new 10-stage funnel (2026-06-02 restructure)
    address: Mapped[str | None] = deferred(mapped_column(Text))            # full postal address
    inquiry_date: Mapped[date | None] = mapped_column(Date)                # date the buyer inquired
    lead_category: Mapped[str | None] = mapped_column(String(5))           # A / B / C
    buyer_engagement_frequency: Mapped[str | None] = mapped_column(String(20))  # Frequent / Medium / Low
    next_action_plan: Mapped[str | None] = deferred(mapped_column(Text))   # mandatory for new leads
    lost_reason: Mapped[str | None] = mapped_column(String(100))           # mandatory when status = Lost
    legacy_status: Mapped[str | None] = mapped_column(String(50))          # pre-migration status preserved
    # Sprint 2 — Lead progression from task outcome
    interest_level: Mapped[str | None] = mapped_column(String(20))          # LOW, MEDIUM, HIGH, VERY_HIGH
    potential_deal_value: Mapped[str | None] = mapped_column(String(50))   # e.g., "50000", "100000-200000"
    customer_requirements: Mapped[str | None] = deferred(mapped_column(Text))
    # Sprint 3 — Pipeline momentum indicator
    has_pending_followup: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")

    followups: Mapped[list["FollowUp"]] = relationship(
        back_populates="lead",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    activity_logs: Mapped[list["ActivityLog"]] = relationship(back_populates="lead", lazy="select")


class FollowUp(Base):
    """Follow-up activity for a lead."""

    __tablename__ = "followups"
    __table_args__ = (
        Index("ix_followups_lead_date", "lead_id", "followup_date"),
        Index("ix_followups_lead_next", "lead_id", "next_followup"),
        Index("ix_followups_next_followup", "next_followup"),
    )

    followup_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lead_id: Mapped[str] = mapped_column(String(32), ForeignKey("leads.lead_id"), nullable=False)
    legacy_buyer_id: Mapped[str | None] = mapped_column(String(50), index=True)
    buyer_name: Mapped[str | None] = mapped_column(String(255))
    country: Mapped[str | None] = mapped_column(String(100))
    assigned_to: Mapped[str | None] = mapped_column(String(100))
    transfer_to: Mapped[str | None] = mapped_column(String(100))
    followup_date: Mapped[date | None] = mapped_column(Date)
    discussion: Mapped[str | None] = mapped_column(Text)
    next_action: Mapped[str | None] = mapped_column(String(255))
    next_followup: Mapped[date | None] = mapped_column(Date)
    mode: Mapped[str | None] = mapped_column(String(50))
    status: Mapped[str | None] = mapped_column(String(50))
    updated_by: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    outcome_notes: Mapped[str | None] = mapped_column(Text)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    completed_by: Mapped[str | None] = mapped_column(String(100))

    lead: Mapped[Lead] = relationship(back_populates="followups", lazy="joined")


class ActivityLog(Base):
    """Audit trail and future activity timeline."""

    __tablename__ = "activity_logs"
    __table_args__ = (
        Index("ix_activity_logs_lead_timestamp", "lead_id", "timestamp"),
        Index("ix_activity_logs_timestamp", "timestamp"),
        Index("ix_activity_logs_action", "action"),
    )

    log_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    user_name: Mapped[str | None] = mapped_column(String(100))
    lead_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("leads.lead_id"))
    remarks: Mapped[str | None] = mapped_column(Text)

    lead: Mapped[Lead | None] = relationship(back_populates="activity_logs", lazy="select")


class DuplicateReport(Base):
    """Potential duplicate lead pair for review."""

    __tablename__ = "duplicate_reports"
    __table_args__ = (
        Index("ix_duplicate_reports_status", "status"),
        UniqueConstraint("lead_1", "lead_2", name="uq_duplicate_pair"),
    )

    duplicate_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lead_1: Mapped[str] = mapped_column(String(32), ForeignKey("leads.lead_id"), nullable=False)
    lead_2: Mapped[str] = mapped_column(String(32), ForeignKey("leads.lead_id"), nullable=False)
    similarity_score: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="PENDING")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class CrmAlert(Base):
    """System-generated alerts for lead health, overdue tasks, etc."""

    __tablename__ = "crm_alerts"
    __table_args__ = (
        Index("ix_crm_alerts_lead", "lead_id"),
        Index("ix_crm_alerts_is_read", "is_read"),
        Index("ix_crm_alerts_created", "created_at"),
    )

    alert_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lead_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("leads.lead_id"), index=True)
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)  # no_followup, inactive, overdue_task, inquiry_overdue
    message: Mapped[str] = mapped_column(Text, nullable=False)
    assigned_to: Mapped[str | None] = mapped_column(String(100))
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class User(Base, TimestampMixin, SoftDeleteMixin):
    """Application user for Streamlit session authentication."""

    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("username", name="uq_users_username"),
        Index("ix_users_role", "role"),
    )

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(100), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    role: Mapped[str] = mapped_column(String(30), nullable=False, default="Salesperson")
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class AppSetting(Base, TimestampMixin):
    """Key-value settings for CRM dropdowns and reminder thresholds."""

    __tablename__ = "app_settings"

    setting_key: Mapped[str] = mapped_column(String(100), primary_key=True)
    setting_value: Mapped[str] = mapped_column(Text, nullable=False)


class LeadSequence(Base):
    """MySQL-backed sequence for CRM lead IDs."""

    __tablename__ = "lead_sequences"

    year: Mapped[int] = mapped_column(Integer, primary_key=True)
    last_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class OrderTracker(Base, TimestampMixin):
    """Order and conversion tracking from the Google Sheet Order_Tracker tab."""

    __tablename__ = "order_tracker"
    __table_args__ = (
        Index("ix_order_tracker_lead_id", "lead_id"),
        Index("ix_order_tracker_status", "order_status"),
        Index("ix_order_tracker_handled_by", "handled_by"),
    )

    order_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lead_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("leads.lead_id"))
    legacy_buyer_id: Mapped[str | None] = mapped_column(String(50), index=True)
    buyer_name: Mapped[str | None] = mapped_column(String(255))
    product: Mapped[str | None] = mapped_column(String(255))
    category: Mapped[str | None] = mapped_column(String(120))
    quantity: Mapped[str | None] = mapped_column(String(100))
    order_value: Mapped[float | None] = mapped_column(Numeric(14, 2))
    currency: Mapped[str | None] = mapped_column(String(20))
    order_date: Mapped[date | None] = mapped_column(Date)
    dispatch_date: Mapped[date | None] = mapped_column(Date)
    payment_terms: Mapped[str | None] = mapped_column(String(255))
    payment_status: Mapped[str | None] = mapped_column(String(50))
    order_status: Mapped[str | None] = mapped_column(String(50))
    handled_by: Mapped[str | None] = mapped_column(String(100))


class EngagementEvent(Base):
    """Per-lead engagement history (calls, WhatsApp, email, meetings, notes).

    Phase A foundation for lead scoring and weekly team analytics. Every touch a
    salesperson logs becomes a row here so response/interaction history accrues
    over time — data the system previously did not capture at all.
    """

    __tablename__ = "engagement_events"
    __table_args__ = (
        Index("ix_engagement_lead_id", "lead_id"),
        Index("ix_engagement_user", "user_name"),
        Index("ix_engagement_type", "event_type"),
        Index("ix_engagement_occurred", "occurred_at"),
    )

    event_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lead_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("leads.lead_id"))
    user_name: Mapped[str | None] = mapped_column(String(100))
    # call | whatsapp | email | meeting | note | status_change | followup
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    channel: Mapped[str | None] = mapped_column(String(40))
    direction: Mapped[str | None] = mapped_column(String(20))  # outbound | inbound
    outcome: Mapped[str | None] = mapped_column(String(60))    # answered | no_answer | replied | etc.
    notes: Mapped[str | None] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class DeletedLead(Base):
    """Audit log of deleted leads (Phase 3) — full snapshot kept for zero data loss."""

    __tablename__ = "deleted_leads"
    __table_args__ = (Index("ix_deleted_leads_lead_id", "lead_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lead_id: Mapped[str | None] = mapped_column(String(32))
    company_name: Mapped[str | None] = mapped_column(String(255))
    contact_name: Mapped[str | None] = mapped_column(String(255))
    assigned_to: Mapped[str | None] = mapped_column(String(100))
    deleted_by: Mapped[str | None] = mapped_column(String(100))
    deleted_date: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    snapshot: Mapped[str | None] = mapped_column(Text)  # full JSON of the lead row


class LeadTransfer(Base):
    """History of lead ownership transfers (Phase 4)."""

    __tablename__ = "lead_transfers"
    __table_args__ = (Index("ix_lead_transfers_lead_id", "lead_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lead_id: Mapped[str] = mapped_column(String(32), nullable=False)
    transferred_from: Mapped[str | None] = mapped_column(String(100))
    transferred_to: Mapped[str | None] = mapped_column(String(100))
    transfer_date: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    transferred_by: Mapped[str | None] = mapped_column(String(100))


class LeadHandover(Base):
    """Pending lead transfer requests with accept/decline workflow."""

    __tablename__ = "lead_handovers"
    __table_args__ = (
        Index("ix_lead_handovers_lead_id", "lead_id"),
        Index("ix_lead_handovers_to_user", "to_user"),
        Index("ix_lead_handovers_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lead_id: Mapped[str] = mapped_column(String(32), nullable=False)
    from_user: Mapped[str] = mapped_column(String(100), nullable=False)
    to_user: Mapped[str] = mapped_column(String(100), nullable=False)
    reason: Mapped[str] = mapped_column(String(50), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    requested_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime)
    responded_by: Mapped[str | None] = mapped_column(String(100))
    created_by: Mapped[str] = mapped_column(String(100), nullable=False)


class ErrorLog(Base):
    """Captured runtime errors (Phase 7) — no silent failures."""

    __tablename__ = "error_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    module: Mapped[str | None] = mapped_column(String(100))
    error: Mapped[str | None] = mapped_column(Text)
    user_name: Mapped[str | None] = mapped_column(String(100))
    traceback: Mapped[str | None] = mapped_column(Text)


class Inquiry(Base, TimestampMixin):
    """Sales inquiry from a Salesperson to Procurement/Operations."""

    __tablename__ = "inquiries"
    __table_args__ = (
        Index("ix_inquiries_lead_id", "lead_id"),
        Index("ix_inquiries_status", "status"),
        Index("ix_inquiries_assigned_to", "assigned_to"),
        Index("ix_inquiries_created_by", "created_by"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lead_id: Mapped[str] = mapped_column(String(32), ForeignKey("leads.lead_id"), nullable=False)
    created_by: Mapped[str] = mapped_column(String(100), nullable=False)
    assigned_to: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    priority: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    response: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="OPEN")
    responded_at: Mapped[datetime | None] = mapped_column(DateTime)
    commitment_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    expected_response_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    committed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # legacy columns — kept for backward compatibility, no longer used
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    estimated_response_time: Mapped[str | None] = mapped_column(String(50), nullable=True)
    acknowledgement_note: Mapped[str | None] = mapped_column(Text, nullable=True)
