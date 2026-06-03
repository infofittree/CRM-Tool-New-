"""Business-facing lead manager for future FastAPI/Streamlit layers."""

from __future__ import annotations

from typing import Any

from database.crud import ActivityLogCRUD, LeadCRUD
from database.db_connection import DatabaseConnection


class LeadManager:
    """High-level lead service with audit logging."""

    def __init__(self, db: DatabaseConnection) -> None:
        self.db = db
        self.leads = LeadCRUD()
        self.activity = ActivityLogCRUD()

    def create_lead(self, payload: dict[str, Any], user_name: str | None = None):
        """Create a lead and audit the action."""
        with self.db.session_scope() as session:
            lead = self.leads.create_lead(session, payload)
            self.activity.log_activity(session, "CREATE_LEAD", user_name, lead.lead_id)
            return lead

    def update_lead(self, lead_id: str, payload: dict[str, Any], user_name: str | None = None):
        """Update a lead and audit the action."""
        with self.db.session_scope() as session:
            lead = self.leads.update_lead(session, lead_id, payload)
            self.activity.log_activity(session, "UPDATE_LEAD", user_name, lead_id)
            return lead

    def search_leads(self, query: str, page: int = 1, page_size: int = 100):
        """Search leads with pagination."""
        with self.db.session_scope() as session:
            return self.leads.search_leads(session, query, page, page_size)

