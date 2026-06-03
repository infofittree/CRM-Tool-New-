"""Read cleaned preprocessing outputs for MySQL import."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


class CleanedExcelImporter:
    """Load cleaned Excel or CSV artifacts from Phase 1."""

    def read_cleaned_workbook(self, path: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Return leads, followups, orders, and duplicate report dataframes."""
        if path.suffix.lower() == ".csv":
            leads = pd.read_csv(path, dtype=object)
            return leads.where(pd.notna(leads), None), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

        workbook = pd.ExcelFile(path, engine="openpyxl")
        leads = self._read_sheet(workbook, "clean_leads")
        followups = self._read_sheet(workbook, "clean_followups")
        orders = self._read_sheet(workbook, "clean_orders")
        duplicates = self._read_sheet(workbook, "duplicate_report")
        return leads, followups, orders, duplicates

    @staticmethod
    def _read_sheet(workbook: pd.ExcelFile, sheet_name: str) -> pd.DataFrame:
        if sheet_name not in workbook.sheet_names:
            return pd.DataFrame()
        return pd.read_excel(workbook, sheet_name=sheet_name, dtype=object).where(lambda df: pd.notna(df), None)
