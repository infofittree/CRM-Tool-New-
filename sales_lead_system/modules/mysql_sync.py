"""MySQL import, synchronization, backup, and export engine."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from openpyxl.styles import Font, PatternFill
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from config.settings import BACKUP_DIR, EXPORT_DIR
from database.crud import ActivityLogCRUD, DuplicateReportCRUD, FollowUpCRUD, LeadCRUD
from database.db_connection import DatabaseConnection
from database.models import DuplicateReport, FollowUp, Lead, OrderTracker
from modules.excel_importer import CleanedExcelImporter
from modules.validation_engine import ValidationEngine


LEAD_COLUMNS = [
    "lead_id",
    "legacy_buyer_id",
    "buyer_tag",
    "company_name",
    "website",
    "industry",
    "city",
    "continent",
    "contact_person",
    "designation",
    "phone",
    "alternate_number",
    "whatsapp_number",
    "email",
    "country",
    "status",
    "assigned_to",
    "transfer_to",
    "lead_source",
    "product_interest",
    "probability",
    "follow_up_stage",
    "mode",
    "quotation_status",
    "moq_requirement",
    "expected_quantity",
    "budget_range",
    "priority_level",
    "remarks",
    "procurement_remarks",
    "internal_notes",
    "created_date",
    "lead_score",
    "last_contact_date",
    # Phase 3 — aligned with updated Google Sheet (2026-06-01)
    "first_contact_date",
    "sheet_source",
]

FOLLOWUP_COLUMNS = [
    "lead_id",
    "legacy_buyer_id",
    "buyer_name",
    "country",
    "assigned_to",
    "transfer_to",
    "followup_date",
    "discussion",
    "next_action",
    "next_followup",
    "mode",
    "status",
    "updated_by",
]

ORDER_COLUMNS = [
    "lead_id",
    "legacy_buyer_id",
    "buyer_name",
    "product",
    "category",
    "quantity",
    "order_value",
    "currency",
    "order_date",
    "dispatch_date",
    "payment_terms",
    "payment_status",
    "order_status",
    "handled_by",
]


@dataclass
class SyncSummary:
    """Import/sync summary for audit and scheduler use."""

    run_id: str
    source_file: str
    inserted_rows: int = 0
    updated_rows: int = 0
    skipped_rows: int = 0
    failed_rows: int = 0
    duplicate_reports: int = 0
    followups_inserted: int = 0
    orders_inserted: int = 0
    errors: list[dict[str, Any]] = field(default_factory=list)
    report_path: str | None = None


class MySQLSyncEngine:
    """Synchronize cleaned Excel artifacts into MySQL."""

    def __init__(self, db: DatabaseConnection, logger: logging.Logger) -> None:
        self.db = db
        self.logger = logger
        self.importer = CleanedExcelImporter()
        self.validator = ValidationEngine()
        self.leads = LeadCRUD(self.validator)
        self.followups = FollowUpCRUD(self.validator)
        self.activity = ActivityLogCRUD()
        self.duplicates = DuplicateReportCRUD()

    def import_cleaned_excel(self, cleaned_file: Path, user_name: str = "system") -> SyncSummary:
        """Insert or update MySQL rows from a cleaned Phase 1 workbook."""
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        summary = SyncSummary(run_id=run_id, source_file=str(cleaned_file))
        self.backup_database_snapshot(run_id)

        leads_df, followups_df, orders_df, duplicate_df = self.importer.read_cleaned_workbook(cleaned_file)
        leads_df = self._normalize_dataframe(leads_df, LEAD_COLUMNS)
        followups_df = self._normalize_dataframe(followups_df, FOLLOWUP_COLUMNS)
        orders_df = self._normalize_dataframe(orders_df, ORDER_COLUMNS)

        with self.db.session_scope() as session:
            existing_by_id = {lead.lead_id: lead for lead in session.scalars(select(Lead))}
            existing_company = {
                self._norm(lead.company_name): lead.lead_id
                for lead in existing_by_id.values()
                if lead.company_name and lead.deleted_at is None
            }
            existing_email = {
                self._norm(lead.email): lead.lead_id
                for lead in existing_by_id.values()
                if lead.email and lead.deleted_at is None
            }
            existing_followups = {
                self._followup_key(item)
                for item in session.scalars(select(FollowUp))
            }
            existing_orders = {
                self._order_key(item)
                for item in session.scalars(select(OrderTracker))
            }

            for row_number, row in enumerate(leads_df.to_dict("records"), start=2):
                payload = self._clean_payload(row, LEAD_COLUMNS)
                result = self.validator.validate_lead_payload(payload)
                if not result.is_valid:
                    summary.failed_rows += 1
                    summary.errors.append({"row": row_number, "lead_id": payload.get("lead_id"), "errors": result.errors})
                    self.logger.warning("Validation failed for lead row %s: %s", row_number, result.errors)
                    continue

                try:
                    lead_id = str(payload["lead_id"])
                    existing = existing_by_id.get(lead_id)
                    duplicate_company_id = existing_company.get(self._norm(payload.get("company_name")))
                    duplicate_email_id = existing_email.get(self._norm(payload.get("email")))

                    if existing is None and duplicate_company_id and duplicate_company_id != lead_id:
                        summary.skipped_rows += 1
                        summary.errors.append(
                            {
                                "row": row_number,
                                "lead_id": lead_id,
                                "errors": [f"duplicate company already exists as {duplicate_company_id}"],
                            }
                        )
                        continue
                    if existing is None and duplicate_email_id and duplicate_email_id != lead_id:
                        summary.skipped_rows += 1
                        summary.errors.append(
                            {
                                "row": row_number,
                                "lead_id": lead_id,
                                "errors": [f"duplicate email already exists as {duplicate_email_id}"],
                            }
                        )
                        continue

                    if existing is None:
                        lead = self.leads.create_lead(session, payload)
                        existing_by_id[lead.lead_id] = lead
                        existing_company[self._norm(lead.company_name)] = lead.lead_id
                        if lead.email:
                            existing_email[self._norm(lead.email)] = lead.lead_id
                        summary.inserted_rows += 1
                        self.activity.log_activity(session, "IMPORT_LEAD", user_name, lead.lead_id)
                    elif self._has_changes(existing, payload):
                        self.leads.update_lead(session, lead_id, payload)
                        summary.updated_rows += 1
                        self.activity.log_activity(session, "UPDATE_FROM_EXCEL", user_name, lead_id)
                    else:
                        summary.skipped_rows += 1
                except (SQLAlchemyError, ValueError, LookupError) as exc:
                    summary.failed_rows += 1
                    summary.errors.append({"row": row_number, "lead_id": payload.get("lead_id"), "errors": [str(exc)]})
                    self.logger.exception("Failed to import lead row %s", row_number)

            try:
                session.flush()
            except SQLAlchemyError as flush_exc:
                session.rollback()
                self.logger.error("Flush failed — rolling back and retrying row-by-row: %s", flush_exc)
                # Retry: insert each lead individually so one conflict doesn't abort all
                for row_number, row in enumerate(leads_df.to_dict("records"), start=2):
                    payload = self._clean_payload(row, LEAD_COLUMNS)
                    try:
                        with self.db.session_scope() as retry_session:
                            lead_id = str(payload.get("lead_id", ""))
                            existing = retry_session.get(Lead, lead_id) if lead_id else None
                            if existing is None:
                                self.leads.create_lead(retry_session, payload)
                                summary.inserted_rows += 1
                            elif self._has_changes(existing, payload):
                                self.leads.update_lead(retry_session, lead_id, payload)
                                summary.updated_rows += 1
                    except (SQLAlchemyError, ValueError, LookupError) as exc:
                        summary.failed_rows += 1
                        summary.errors.append({"row": row_number, "lead_id": payload.get("lead_id"), "errors": [str(exc)]})
                # Re-open session for followups/orders
                with self.db.session_scope() as session:
                    for row in followups_df.to_dict("records"):
                        payload = self._clean_payload(row, FOLLOWUP_COLUMNS)
                        key = self._followup_key(payload)
                        if payload.get("lead_id") and key not in set():
                            try:
                                self.followups.add_followup(session, payload)
                                summary.followups_inserted += 1
                            except (SQLAlchemyError, ValueError):
                                pass
                    for row in orders_df.to_dict("records"):
                        payload = self._clean_payload(row, ORDER_COLUMNS)
                        if payload.get("lead_id") or payload.get("legacy_buyer_id"):
                            try:
                                session.add(OrderTracker(**{c: payload.get(c) for c in ORDER_COLUMNS}))
                                summary.orders_inserted += 1
                            except (SQLAlchemyError, ValueError):
                                pass
                summary.report_path = str(self._write_sync_report(summary))
                return summary

            for row in followups_df.to_dict("records"):
                payload = self._clean_payload(row, FOLLOWUP_COLUMNS)
                key = self._followup_key(payload)
                if payload.get("lead_id") in existing_by_id and key not in existing_followups:
                    try:
                        followup = self.followups.add_followup(session, payload)
                        existing_followups.add(self._followup_key(followup))
                        summary.followups_inserted += 1
                    except (SQLAlchemyError, ValueError, LookupError) as exc:
                        self.logger.warning("Skipping followup row: %s", exc)

            for row in orders_df.to_dict("records"):
                payload = self._clean_payload(row, ORDER_COLUMNS)
                key = self._order_key(payload)
                if (payload.get("lead_id") in existing_by_id or payload.get("legacy_buyer_id")) and key not in existing_orders:
                    try:
                        order = OrderTracker(**{column: payload.get(column) for column in ORDER_COLUMNS})
                        session.add(order)
                        existing_orders.add(self._order_key(order))
                        summary.orders_inserted += 1
                    except (SQLAlchemyError, ValueError) as exc:
                        self.logger.warning("Skipping order row: %s", exc)

            summary.duplicate_reports = self._persist_duplicate_reports(session, duplicate_df, set(existing_by_id))

        summary.report_path = str(self._write_sync_report(summary))
        return summary

    def export_all(self, export_dir: Path | None = None) -> dict[str, str]:
        """Export leads to Excel, followups to CSV, and reports to Excel."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_dir = export_dir or EXPORT_DIR / timestamp
        export_dir.mkdir(parents=True, exist_ok=True)

        with self.db.session_scope() as session:
            leads = pd.DataFrame([self._model_to_dict(lead, LEAD_COLUMNS + ["created_at", "updated_at"]) for lead in session.scalars(select(Lead))])
            followups = pd.DataFrame([self._model_to_dict(item, ["followup_id"] + FOLLOWUP_COLUMNS + ["created_at"]) for item in session.scalars(select(FollowUp))])
            orders = pd.DataFrame([self._model_to_dict(item, ["order_id"] + ORDER_COLUMNS + ["created_at", "updated_at"]) for item in session.scalars(select(OrderTracker))])
            duplicates = pd.DataFrame(
                [
                    self._model_to_dict(item, ["duplicate_id", "lead_1", "lead_2", "similarity_score", "status", "created_at"])
                    for item in session.scalars(select(DuplicateReport))
                ]
            )

        leads_excel = export_dir / "leads_export.xlsx"
        reports_excel = export_dir / "reports_export.xlsx"
        followups_csv = export_dir / "followups_export.csv"
        orders_excel = export_dir / "orders_export.xlsx"

        with pd.ExcelWriter(leads_excel, engine="openpyxl") as writer:
            leads.to_excel(writer, sheet_name="leads", index=False)
            self._format_worksheet(writer, "leads")

        followups.to_csv(followups_csv, index=False)
        with pd.ExcelWriter(orders_excel, engine="openpyxl") as writer:
            orders.to_excel(writer, sheet_name="order_tracker", index=False)
            self._format_worksheet(writer, "order_tracker")

        with pd.ExcelWriter(reports_excel, engine="openpyxl") as writer:
            duplicates.to_excel(writer, sheet_name="duplicate_reports", index=False)
            self._format_worksheet(writer, "duplicate_reports")

        return {
            "leads_excel": str(leads_excel),
            "followups_csv": str(followups_csv),
            "orders_excel": str(orders_excel),
            "reports_excel": str(reports_excel),
        }

    def backup_database_snapshot(self, run_id: str) -> Path:
        """Create a lightweight JSON backup before sync."""
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        backup_path = BACKUP_DIR / f"mysql_snapshot_{run_id}.json"
        snapshot: dict[str, list[dict[str, Any]]] = {"leads": [], "followups": [], "orders": [], "duplicate_reports": []}
        try:
            with self.db.session_scope() as session:
                snapshot["leads"] = [self._model_to_dict(lead, LEAD_COLUMNS + ["created_at", "updated_at"]) for lead in session.scalars(select(Lead))]
                snapshot["followups"] = [
                    self._model_to_dict(item, ["followup_id"] + FOLLOWUP_COLUMNS + ["created_at"])
                    for item in session.scalars(select(FollowUp))
                ]
                snapshot["orders"] = [
                    self._model_to_dict(item, ["order_id"] + ORDER_COLUMNS + ["created_at", "updated_at"])
                    for item in session.scalars(select(OrderTracker))
                ]
                snapshot["duplicate_reports"] = [
                    self._model_to_dict(item, ["duplicate_id", "lead_1", "lead_2", "similarity_score", "status", "created_at"])
                    for item in session.scalars(select(DuplicateReport))
                ]
        except SQLAlchemyError:
            self.logger.exception("Database backup failed before sync")
            raise
        with backup_path.open("w", encoding="utf-8") as handle:
            json.dump(snapshot, handle, indent=2, default=str)
        return backup_path

    def _persist_duplicate_reports(self, session, duplicate_df: pd.DataFrame, existing_ids: set[str]) -> int:
        if duplicate_df.empty:
            return 0
        count = 0
        for row in duplicate_df.to_dict("records"):
            lead_1 = row.get("lead_id_1") or row.get("lead_1")
            lead_2 = row.get("lead_id_2") or row.get("lead_2")
            score = row.get("similarity_score") or 0
            if lead_1 and lead_2 and str(lead_1) in existing_ids and str(lead_2) in existing_ids:
                self.duplicates.create_or_update_duplicate(session, str(lead_1), str(lead_2), float(score))
                count += 1
        return count

    def _write_sync_report(self, summary: SyncSummary) -> Path:
        report_dir = EXPORT_DIR / "sync_reports"
        report_dir.mkdir(parents=True, exist_ok=True)
        path = report_dir / f"sync_report_{summary.run_id}.json"
        with path.open("w", encoding="utf-8") as handle:
            json.dump(asdict(summary), handle, indent=2, default=str)
        return path

    @staticmethod
    def _normalize_dataframe(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
        if df.empty:
            return pd.DataFrame(columns=columns)
        normalized = df.copy()
        normalized.columns = [str(column).strip() for column in normalized.columns]
        for column in columns:
            if column not in normalized.columns:
                normalized[column] = None
        return normalized[columns].where(pd.notna(normalized[columns]), None)

    @staticmethod
    def _clean_payload(row: dict[str, Any], columns: list[str]) -> dict[str, Any]:
        payload = {column: row.get(column) for column in columns}
        # NOT NULL columns with no Google Sheet equivalent — supply defaults
        if not payload.get("lead_score"):
            payload["lead_score"] = 0.0
        if not payload.get("priority_level"):
            payload["priority_level"] = "MEDIUM"
        if not payload.get("status"):
            payload["status"] = "NEW"
        for date_field in ("created_date", "last_contact_date", "first_contact_date", "followup_date", "next_followup", "order_date", "dispatch_date"):
            if payload.get(date_field):
                parsed = pd.to_datetime(payload[date_field], errors="coerce")
                if pd.isna(parsed):
                    payload[date_field] = None
                else:
                    payload[date_field] = parsed.date()
        return payload

    @staticmethod
    def _has_changes(existing: Lead, payload: dict[str, Any]) -> bool:
        for key, value in payload.items():
            if hasattr(existing, key) and str(getattr(existing, key) or "") != str(value or ""):
                return True
        return False

    @staticmethod
    def _norm(value: Any) -> str:
        return str(value or "").strip().upper()

    @staticmethod
    def _model_to_dict(model: Any, columns: list[str]) -> dict[str, Any]:
        return {column: getattr(model, column, None) for column in columns}

    @staticmethod
    def _followup_key(item: Any) -> tuple[str, str, str, str, str]:
        getter = item.get if isinstance(item, dict) else lambda key: getattr(item, key, None)
        return (
            str(getter("lead_id") or ""),
            str(getter("followup_date") or ""),
            str(getter("discussion") or "").strip(),
            str(getter("next_action") or "").strip(),
            str(getter("next_followup") or ""),
        )

    @staticmethod
    def _order_key(item: Any) -> tuple[str, str, str, str, str, str]:
        getter = item.get if isinstance(item, dict) else lambda key: getattr(item, key, None)
        return (
            str(getter("lead_id") or ""),
            str(getter("legacy_buyer_id") or ""),
            str(getter("product") or "").strip(),
            str(getter("order_date") or ""),
            str(getter("order_value") or ""),
            str(getter("order_status") or "").strip(),
        )

    @staticmethod
    def _format_worksheet(writer: pd.ExcelWriter, sheet_name: str) -> None:
        worksheet = writer.sheets[sheet_name]
        worksheet.freeze_panes = "A2"
        for cell in worksheet[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="1F4E78")
        for column_cells in worksheet.columns:
            values = [str(cell.value or "") for cell in column_cells]
            width = min(max(max(len(value) for value in values) + 2, 12), 42)
            worksheet.column_dimensions[column_cells[0].column_letter].width = width
