"""Rule-based data validation for cleaned sales lead data."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

import pandas as pd


class DataValidator:
    """Validate required fields, business rules, formats, and duplicate IDs."""

    EMAIL_PATTERN = re.compile(r"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$", re.IGNORECASE)

    def __init__(self, validation_rules_path: Path, logger: logging.Logger) -> None:
        self.logger = logger
        with validation_rules_path.open("r", encoding="utf-8") as handle:
            self.rules: dict[str, Any] = json.load(handle)

    def validate_leads(self, leads: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Return valid leads and row-level validation findings."""
        findings: list[dict[str, Any]] = []
        required = self.rules.get("required_lead_fields", [])
        allowed_statuses = {str(item).casefold() for item in self.rules.get("allowed_statuses", [])}

        for index, row in leads.iterrows():
            row_errors: list[str] = []
            blocking_errors: list[str] = []
            for field in required:
                if field in leads.columns and self._is_empty(row.get(field)):
                    message = f"{field} is required"
                    row_errors.append(message)
                    blocking_errors.append(message)

            status = row.get("status")
            if status and str(status).casefold() not in allowed_statuses:
                row_errors.append(f"status '{status}' is not allowed")
            status_key = str(status or "").casefold()
            # Advisory only — logged to report but never blocks import
            if status_key in {"nurturing", "nurture"} and self._is_empty(row.get("next_follow_up")):
                findings.append({
                    "row_number": int(index) + 2,
                    "lead_id": row.get("lead_id"),
                    "company_name": row.get("company_name"),
                    "errors": "advisory: next_follow_up missing for Nurture lead",
                    "blocking": False,
                })
            if status_key in {"negotiation"} and self._is_empty(row.get("remarks")):
                findings.append({
                    "row_number": int(index) + 2,
                    "lead_id": row.get("lead_id"),
                    "company_name": row.get("company_name"),
                    "errors": "advisory: remarks missing for Negotiation lead",
                    "blocking": False,
                })

            email = row.get("email")
            if not self._is_empty(email) and not self.EMAIL_PATTERN.match(str(email)):
                row_errors.append(f"invalid email format: {email}")

            phone = row.get("phone")
            if not self._is_empty(phone) and len(re.sub(r"\D", "", str(phone))) < 7:
                row_errors.append(f"invalid phone format: {phone}")

            if row_errors:
                findings.append(
                    {
                        "row_number": int(index) + 2,
                        "lead_id": row.get("lead_id"),
                        "company_name": row.get("company_name"),
                        "errors": "; ".join(row_errors),
                        "blocking": bool(blocking_errors),
                    }
                )

        if "lead_id" in leads.columns:
            duplicated_ids = leads[leads["lead_id"].notna() & leads["lead_id"].duplicated(keep=False)]
            for _, row in duplicated_ids.iterrows():
                findings.append(
                    {
                        "row_number": None,
                        "lead_id": row.get("lead_id"),
                        "company_name": row.get("company_name"),
                        "errors": "duplicate lead_id",
                        "blocking": True,
                    }
                )

        report = pd.DataFrame(findings)
        invalid_indexes = set()
        for finding in findings:
            row_number = finding.get("row_number")
            if row_number and finding.get("blocking"):
                invalid_indexes.add(row_number - 2)
        valid = leads.drop(index=[i for i in invalid_indexes if i in leads.index]).copy()
        self.logger.info("Validation complete: %s invalid rows", len(invalid_indexes))
        return valid, report

    @staticmethod
    def _is_empty(value: Any) -> bool:
        return pd.isna(value) or str(value).strip() == ""
