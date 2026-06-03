"""Duplicate lead detection using RapidFuzz when available."""

from __future__ import annotations

import logging
from difflib import SequenceMatcher
from typing import Any

import pandas as pd

try:
    from rapidfuzz import fuzz
except ImportError:  # pragma: no cover - local fallback for first-run environments.
    fuzz = None


class DuplicateDetector:
    """Find likely duplicate company records using names and contact fields."""

    def __init__(self, threshold: int, logger: logging.Logger) -> None:
        self.threshold = threshold
        self.logger = logger
        if fuzz is None:
            self.logger.warning("RapidFuzz is not installed; using difflib fallback for duplicate detection")

    def find_duplicates(self, leads: pd.DataFrame) -> pd.DataFrame:
        """Return possible duplicate pairs with match reasons and score."""
        records = leads.reset_index(drop=True).to_dict("records")
        duplicates: list[dict[str, Any]] = []

        for left_index in range(len(records)):
            for right_index in range(left_index + 1, len(records)):
                left = records[left_index]
                right = records[right_index]
                reasons: list[str] = []

                name_score = self._score(left.get("company_name"), right.get("company_name"))
                if name_score >= self.threshold:
                    reasons.append(f"company_name similarity {name_score}")

                for field in ("phone", "email", "website"):
                    left_value = self._norm(left.get(field))
                    right_value = self._norm(right.get(field))
                    if left_value and right_value and left_value == right_value:
                        reasons.append(f"same {field}")

                if reasons:
                    duplicates.append(
                        {
                            "lead_id_1": left.get("lead_id"),
                            "company_name_1": left.get("company_name"),
                            "lead_id_2": right.get("lead_id"),
                            "company_name_2": right.get("company_name"),
                            "similarity_score": name_score,
                            "match_reasons": "; ".join(reasons),
                        }
                    )

        report = pd.DataFrame(duplicates)
        self.logger.info("Duplicate detection complete: %s possible duplicate pairs", len(report))
        return report

    @staticmethod
    def _norm(value: Any) -> str:
        if pd.isna(value):
            return ""
        return str(value).strip().lower()

    def _score(self, left: Any, right: Any) -> int:
        left_text = self._norm(left)
        right_text = self._norm(right)
        if not left_text or not right_text:
            return 0
        if fuzz is not None:
            return int(fuzz.token_set_ratio(left_text, right_text))
        return int(SequenceMatcher(None, left_text, right_text).ratio() * 100)

