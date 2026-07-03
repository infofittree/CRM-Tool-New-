"""Validation engine for records before MySQL persistence."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from database.models import ALLOWED_STATUSES


EMAIL_PATTERN = re.compile(r"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$", re.IGNORECASE)


@dataclass(frozen=True)
class ValidationResult:
    """Validation result with reusable error payload."""

    is_valid: bool
    errors: list[str]


class ValidationEngine:
    """Validate CRM payloads before insert/update."""

    required_lead_fields = ("lead_id", "status")

    def validate_lead_payload(self, payload: dict[str, Any]) -> ValidationResult:
        """Validate a lead dictionary."""
        errors: list[str] = []
        for field in self.required_lead_fields:
            if self._is_empty(payload.get(field)):
                errors.append(f"{field} is required")

        status = payload.get("status")
        allowed_statuses = {str(item).casefold() for item in ALLOWED_STATUSES}
        if status and str(status).casefold() not in allowed_statuses:
            errors.append(f"status '{status}' is not allowed")

        email = payload.get("email")
        if not self._is_empty(email) and not EMAIL_PATTERN.match(str(email)):
            errors.append(f"invalid email format: {email}")

        phone = payload.get("phone")
        if not self._is_empty(phone) and len(re.sub(r"\D", "", str(phone))) < 7:
            errors.append(f"invalid phone format: {phone}")

        return ValidationResult(not errors, errors)

    def validate_followup_payload(self, payload: dict[str, Any]) -> ValidationResult:
        """Validate a follow-up dictionary."""
        errors: list[str] = []
        if self._is_empty(payload.get("lead_id")):
            errors.append("lead_id is required")
        return ValidationResult(not errors, errors)

    @staticmethod
    def _is_empty(value: Any) -> bool:
        return value is None or str(value).strip() == ""
