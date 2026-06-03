"""Business-facing follow-up manager."""

from __future__ import annotations

from typing import Any

from database.crud import ActivityLogCRUD, FollowUpCRUD
from database.db_connection import DatabaseConnection


class FollowUpManager:
    """High-level follow-up service with audit logging."""

    def __init__(self, db: DatabaseConnection) -> None:
        self.db = db
        self.followups = FollowUpCRUD()
        self.activity = ActivityLogCRUD()

    def add_followup(self, payload: dict[str, Any], user_name: str | None = None):
        """Create a follow-up and audit the action."""
        with self.db.session_scope() as session:
            followup = self.followups.add_followup(session, payload)
            self.activity.log_activity(session, "ADD_FOLLOWUP", user_name, followup.lead_id)
            return followup

    def get_followups(self, lead_id: str):
        """Fetch follow-ups for one lead."""
        with self.db.session_scope() as session:
            return self.followups.get_followups(session, lead_id)

