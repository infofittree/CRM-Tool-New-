"""Pydantic request/response models for the CRM API."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


# ── Auth ──────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    username: str
    full_name: str
    role: str
    phone: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ── Dashboard ─────────────────────────────────────────────────────────────────

class DashboardCounts(BaseModel):
    total: int
    active: int
    nurturing: int
    converted: int
    conversion_rate: float
    overdue_followups: int
    due_today_followups: int


class EngagementStats(BaseModel):
    total: int
    calls: int
    whatsapp: int
    emails: int
    meetings: int
    followups: int
    today_done: int
    by_user: dict[str, int]


# ── Leads ──────────────────────────────────────────────────────────────────────

class LeadResponse(BaseModel):
    lead_id: str
    company_name: str | None = None
    contact_person: str | None = None
    phone: str | None = None
    email: str | None = None
    country: str | None = None
    continent: str | None = None
    status: str | None = None
    assigned_to: str | None = None
    lead_source: str | None = None
    lead_category: str | None = None
    lead_score: float = 0
    priority_level: str = "MEDIUM"
    last_contact_date: date | None = None
    created_date: date | None = None
    next_action_plan: str | None = None
    lost_reason: str | None = None
    industry: str | None = None
    website: str | None = None
    city: str | None = None
    designation: str | None = None
    alternate_number: str | None = None
    whatsapp_number: str | None = None
    product_interest: str | None = None
    inquiry_date: date | None = None
    buyer_engagement_frequency: str | None = None
    remarks: str | None = None
    internal_notes: str | None = None
    procurement_remarks: str | None = None
    interest_level: str | None = None
    potential_deal_value: str | None = None
    customer_requirements: str | None = None
    has_pending_followup: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class LeadCreate(BaseModel):
    company_name: str | None = None
    contact_person: str | None = None
    phone: str | None = None
    email: str | None = None
    country: str | None = None
    status: str = "Prospect"
    assigned_to: str | None = None
    lead_source: str | None = None
    lead_category: str | None = None
    priority_level: str = "MEDIUM"
    next_follow_up: date | None = None
    followup_mode: str | None = None
    last_discussion: str | None = None
    next_action: str | None = None
    next_action_plan: str | None = None
    remarks: str | None = None
    industry: str | None = None
    website: str | None = None
    city: str | None = None
    designation: str | None = None
    alternate_number: str | None = None
    whatsapp_number: str | None = None
    product_interest: str | None = None
    product_ids: list[int] | None = None


class LeadUpdate(BaseModel):
    status: str | None = None
    assigned_to: str | None = None
    lead_category: str | None = None
    buyer_engagement_frequency: str | None = None
    next_action_plan: str | None = None
    lost_reason: str | None = None
    remarks: str | None = None
    internal_notes: str | None = None
    procurement_remarks: str | None = None
    priority_level: str | None = None
    interest_level: str | None = None
    potential_deal_value: str | None = None
    customer_requirements: str | None = None
    product_ids: list[int] | None = None


class LeadTransfer(BaseModel):
    new_owner: str
    reason: str | None = None


class QuickFollowup(BaseModel):
    discussion: str | None = None
    next_action: str | None = None
    next_followup: date | None = None
    mode: str | None = None
    status: str | None = None
    lost_reason: str | None = None


class RescheduleRequest(BaseModel):
    new_date: date
    note: str | None = None


class NoteRequest(BaseModel):
    note: str


class DuplicateCheckResult(BaseModel):
    lead_id: str
    company_name: str | None
    similarity: int
    reasons: str


# ── Follow-ups ────────────────────────────────────────────────────────────────

class FollowUpResponse(BaseModel):
    followup_id: int
    lead_id: str
    followup_date: date | None = None
    discussion: str | None = None
    next_action: str | None = None
    next_followup: date | None = None
    mode: str | None = None
    status: str | None = None
    updated_by: str | None = None
    created_at: datetime | None = None
    outcome_notes: str | None = None
    completed_at: datetime | None = None
    completed_by: str | None = None

    model_config = {"from_attributes": True}


class FollowUpCreate(BaseModel):
    lead_id: str
    followup_date: date | None = None
    discussion: str | None = None
    next_action: str | None = None
    next_followup: date | None = None
    mode: str | None = None
    status: str | None = None
    updated_by: str | None = None
    outcome_notes: str | None = None


class FollowUpComplete(BaseModel):
    outcome_notes: str
    # Lead progression fields (optional — populated from task outcome drawer)
    lead_status: str | None = None
    interest_level: str | None = None
    potential_deal_value: str | None = None
    customer_requirements: str | None = None
    discussion_summary: str | None = None  # updates follow-up discussion field
    # Sprint 3 — Next action & auto task creation
    next_action_type: str | None = None
    next_followup_date: date | None = None


class FollowUpCompleteResponse(BaseModel):
    followup: FollowUpResponse
    next_followup: FollowUpResponse | None = None


class ActivityWizardRequest(BaseModel):
    actions: list[str]
    call_outcome: str | None = None
    customer_interest: str | None = None
    expect_response: bool | None = None
    response_check_date: str | None = None
    meeting_outcome: str | None = None
    customer_requirements: list[str] | None = None
    not_interested_reason: str | None = None
    notes: str | None = None
    followup_date: str | None = None
    next_followup_mode: str | None = None


class ActivityWizardResponse(BaseModel):
    followup_id: int
    next_followup_id: int | None = None
    next_action_type: str | None = None
    next_action_template: str | None = None
    next_followup_date: str | None = None
    lead_status: str | None = None
    lead_interest: str | None = None
    lead_updates: list[str] = []
    timeline_entries: list[str] = []


class TaskResponse(BaseModel):
    lead_id: str
    company_name: str
    contact_person: str | None = None
    phone: str | None = None
    email: str | None = None
    status: str
    standard_status: str
    lead_category: str | None = None
    lead_score: float
    score_band: str
    assigned_to: str | None = None
    due_date: date | None = None
    days_to: int
    priority: int
    recommended_action: str
    next_action_plan: str | None = None
    followup_id: int | None = None
    discussion: str | None = None
    next_action: str | None = None
    outcome_notes: str | None = None
    completed_at: datetime | None = None
    completed_by: str | None = None


class TaskQueue(BaseModel):
    today_capped: list[dict]
    upcoming: list[dict]
    overdue: list[dict]
    completed: list[dict] = []
    summary: dict[str, int]


# ── Users ──────────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    username: str
    password: str
    full_name: str
    role: str = "Salesperson"
    phone: str | None = None

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        allowed = {"Admin", "Manager", "Salesperson", "Procurement"}
        if v not in allowed:
            raise ValueError(f"Role must be one of: {', '.join(sorted(allowed))}")
        return v


class UserDelete(BaseModel):
    mode: str = "transfer"
    transfer_to: str | None = None


class UserWorkload(BaseModel):
    total: int


# ── Inquiries ─────────────────────────────────────────────────────────────────

class InquiryCreate(BaseModel):
    lead_id: str
    title: str
    type: str = "PRICING"
    priority: str = "MEDIUM"
    description: str | None = None


class InquiryResponse(BaseModel):
    id: int
    lead_id: str
    created_by: str
    assigned_to: str
    title: str
    type: str
    priority: str
    description: str | None = None
    response: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime
    responded_at: datetime | None = None
    commitment_type: str | None = None
    expected_response_date: datetime | None = None
    committed_at: datetime | None = None


class InquiryUpdate(BaseModel):
    response: str | None = None
    status: str | None = None


class InquiryDetail(BaseModel):
    id: int
    lead_id: str
    created_by: str
    assigned_to: str
    title: str
    type: str
    priority: str
    description: str | None = None
    response: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime
    responded_at: datetime | None = None
    commitment_type: str | None = None
    expected_response_date: datetime | None = None
    committed_at: datetime | None = None
    company_name: str | None = None
    contact_person: str | None = None


class CommitmentRequest(BaseModel):
    commitment_type: str
    expected_response_date: datetime | None = None
    response: str | None = None


class InquirySummary(BaseModel):
    total_open: int = 0
    eod_committed: int = 0
    pending_response: int = 0
    overdue: int = 0
    responded_today: int = 0


# ── Sprint 4 — Task Intelligence & Pipeline Health ────────────────────────────

class LeadHealthResponse(BaseModel):
    health: str = "healthy"
    risk_level: str = "low"
    warnings: list[str] = []
    last_activity_days: int | None = None
    next_followup_date: date | None = None


class PipelineHealthResponse(BaseModel):
    healthy: int = 0
    attention_needed: int = 0
    at_risk: int = 0
    stalled: int = 0
    total: int = 0


class TodayPrioritiesResponse(BaseModel):
    overdue_tasks: int = 0
    due_today: int = 0
    at_risk_leads: int = 0
    stalled_leads: int = 0
    pending_inquiries: int = 0
    leads_without_followup: int = 0


class SalespersonKpi(BaseModel):
    assigned_to: str
    tasks_due_today: int = 0
    overdue_tasks: int = 0
    upcoming_tasks: int = 0
    completed_tasks: int = 0
    overdue_pct: float = 0.0
    completion_pct: float = 0.0
    avg_delay_days: float = 0.0


class AlertResponse(BaseModel):
    alert_id: int
    lead_id: str | None = None
    alert_type: str
    message: str
    is_read: bool = False
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


# ── Generic ───────────────────────────────────────────────────────────────────

class ErrorResponse(BaseModel):
    detail: str


class PaginatedResponse(BaseModel):
    items: list[Any]
    total: int
    page: int
    page_size: int


# ── Lead Handover ─────────────────────────────────────────────────────────────

HANDOVER_REASONS = ("product_expertise", "language", "region", "customer_request", "workload", "leave", "manager_decision", "other")

class HandoverCreate(BaseModel):
    to_user: str
    reason: str
    notes: str | None = None

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, v: str) -> str:
        if v not in HANDOVER_REASONS:
            raise ValueError(f"Reason must be one of: {', '.join(HANDOVER_REASONS)}")
        return v


class HandoverResponse(BaseModel):
    id: int
    lead_id: str
    from_user: str
    to_user: str
    reason: str
    notes: str | None = None
    status: str
    requested_at: datetime
    responded_at: datetime | None = None
    responded_by: str | None = None
    created_by: str
    company_name: str | None = None


# ── Products ─────────────────────────────────────────────────────────────────

class ProductCreate(BaseModel):
    name: str
    category: str


class ProductResponse(BaseModel):
    id: int
    name: str
    category: str
    is_active: bool = True
