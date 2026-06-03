"""Data cleaning utilities for raw sales lead workbooks."""

from __future__ import annotations

import json
import logging
import re
import warnings
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd


class DataCleaner:
    """Clean text, statuses, dates, phone numbers, and common CRM fields."""

    def __init__(self, status_mapping_path: Path, logger: logging.Logger) -> None:
        self.logger = logger
        self.status_map = self._load_status_mapping(status_mapping_path)
        self.allowed_statuses = set(self.status_map.get("allowed_statuses", []))
        self.aliases = {
            self._status_key(alias): canonical
            for canonical, aliases in self.status_map.get("aliases", {}).items()
            for alias in aliases
        }

    @staticmethod
    def standardize_column_name(column: Any) -> str:
        """Convert a workbook column name to snake_case."""
        text = str(column).strip().lower()
        text = text.replace("/", " ")
        text = re.sub(r"[^a-z0-9]+", "_", text)
        text = re.sub(r"_+", "_", text).strip("_")
        return text or "unnamed"

    def standardize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Return a copy with normalized and unique column names."""
        output = df.copy()
        seen: dict[str, int] = {}
        columns: list[str] = []
        for column in output.columns:
            name = self.standardize_column_name(column)
            seen[name] = seen.get(name, 0) + 1
            columns.append(name if seen[name] == 1 else f"{name}_{seen[name]}")
        output.columns = columns
        return output

    def clean_text(self, value: Any, uppercase: bool = False, strip_symbols: bool = False) -> str | None:
        """Clean common spreadsheet text values."""
        if pd.isna(value):
            return None
        text = str(value).strip()
        text = re.sub(r"\s+", " ", text)
        if strip_symbols:
            text = re.sub(r"[^\w\s.&@+\-]", "", text)
        if uppercase:
            text = text.upper()
        return text or None

    def clean_company_name(self, value: Any) -> str | None:
        """Normalize company names for CRM display and matching."""
        text = self.clean_text(value, uppercase=True, strip_symbols=True)
        if not text:
            return None
        suffixes = [
            r"\bPRIVATE LIMITED\b",
            r"\bPVT\.?\s*LTD\.?\b",
            r"\bPVT\b",
            r"\bLTD\.?\b",
            r"\bLIMITED\b",
            r"\bLLC\b",
            r"\bINC\.?\b",
            r"\bCO\.?\b",
        ]
        for suffix in suffixes:
            text = re.sub(suffix, "", text)
        text = re.sub(r"[^\w\s]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text or None

    def clean_country(self, value: Any) -> str | None:
        """Standardize country names using a small configurable-friendly baseline."""
        text = self.clean_text(value, uppercase=True, strip_symbols=True)
        if not text:
            return None
        country_map = {
            "USA": "UNITED STATES",
            "US": "UNITED STATES",
            "U S A": "UNITED STATES",
            "UK": "UNITED KINGDOM",
            "UAE": "UNITED ARAB EMIRATES",
            "KSA": "SAUDI ARABIA",
        }
        return country_map.get(text, text)

    def clean_phone(self, value: Any) -> str | None:
        """Keep a phone number in a database-safe, comparable format."""
        if pd.isna(value):
            return None
        text = str(value).strip()
        if not text:
            return None
        if re.fullmatch(r"\d+\.0", text):
            text = text[:-2]
        text = re.sub(r"[^\d+]", "", text)
        if text.count("+") > 1:
            text = "+" + text.replace("+", "")
        if "+" in text and not text.startswith("+"):
            text = text.replace("+", "")
        return text or None

    def standardize_status(self, value: Any) -> str:
        """Map many raw statuses into the allowed CRM status set."""
        key = self._status_key(value)
        status = self.aliases.get(key)
        if status:
            return status
        if key:
            candidate = key.replace("_", " ").upper()
            if candidate in self.allowed_statuses:
                return candidate
            self.logger.warning("Unknown status '%s'; defaulting to NEW", value)
        return "NEW"

    def normalize_date(self, value: Any, field_name: str = "date") -> str | None:
        """Normalize spreadsheet dates to YYYY-MM-DD, logging invalid values."""
        if pd.isna(value) or value == "":
            return None
        if isinstance(value, datetime):
            return value.date().isoformat()
        if isinstance(value, pd.Timestamp):
            return value.date().isoformat()
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            try:
                # Excel's Windows date origin: 1899-12-30.
                return (datetime(1899, 12, 30) + timedelta(days=float(value))).date().isoformat()
            except (OverflowError, ValueError):
                self.logger.warning("Invalid Excel serial date in %s: %r", field_name, value)
                return None

        # Try unambiguous ISO formats first to avoid dayfirst month/day swap
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d"):
            try:
                return datetime.strptime(str(value).strip(), fmt).date().isoformat()
            except ValueError:
                pass

        # Fall back to pandas for European dd/mm/yyyy and other ambiguous formats
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            parsed = pd.to_datetime(value, errors="coerce", dayfirst=True)
        if pd.isna(parsed):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                parsed = pd.to_datetime(value, errors="coerce", dayfirst=False)
        if pd.isna(parsed):
            self.logger.warning("Invalid date in %s: %r", field_name, value)
            return None
        return parsed.date().isoformat()

    def clean_salesperson(self, value: Any) -> str | None:
        """Normalize salesperson names for grouping and assignment."""
        return self.clean_text(value, uppercase=True, strip_symbols=True)

    def clean_email(self, value: Any) -> str | None:
        """Normalize email text."""
        text = self.clean_text(value, uppercase=False)
        return text.lower() if text else None

    # Follow-up sheets have these columns — their "status" is Open/Done/Delayed, not a lead stage
    _FOLLOWUP_SHEET_MARKERS = {"discussion_summary", "next_follow_up_date", "next_followup"}

    def clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply broad cleaning to a standardized dataframe."""
        output = self.standardize_columns(df)
        output = output.dropna(how="all").copy()

        for column in output.select_dtypes(include=["object"]).columns:
            output[column] = output[column].map(lambda x: self.clean_text(x))

        for column in [c for c in output.columns if "company" in c or "buyer_name" in c]:
            output[column] = output[column].map(self.clean_company_name)
        for column in [c for c in output.columns if c == "country"]:
            output[column] = output[column].map(self.clean_country)
        for column in [c for c in output.columns if "assigned" in c or "updated_by" in c or "transfer_to" in c]:
            output[column] = output[column].map(self.clean_salesperson)
        for column in [c for c in output.columns if "email" in c]:
            output[column] = output[column].map(self.clean_email)
        for column in [c for c in output.columns if "phone" in c or "number" in c]:
            output[column] = output[column].map(self.clean_phone)

        # Only normalize lead statuses on lead sheets — follow-up sheets use Open/Done/Delayed
        is_followup_sheet = bool(self._FOLLOWUP_SHEET_MARKERS & set(output.columns))
        if not is_followup_sheet:
            for column in [c for c in output.columns if c == "status"]:
                output[column] = output[column].map(self.standardize_status)

        for column in [
            c
            for c in output.columns
            if "date" in c or c in {"next_followup", "next_follow_up", "next_follow_up_date"}
        ]:
            output[column] = output[column].map(lambda x, col=column: self.normalize_date(x, col))

        return output

    @staticmethod
    def _status_key(value: Any) -> str:
        if pd.isna(value):
            return ""
        text = str(value).strip().lower()
        text = re.sub(r"[^a-z0-9]+", "_", text)
        return re.sub(r"_+", "_", text).strip("_")

    @staticmethod
    def _load_status_mapping(path: Path) -> dict[str, Any]:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
