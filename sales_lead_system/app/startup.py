"""Startup bootstrap for live CRM data flow."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Callable

from sqlalchemy import func, inspect, select
from sqlalchemy.exc import SQLAlchemyError

from app.security import hash_password
from config.settings import LOG_DIR, PROJECT_ROOT
from database.db_connection import DatabaseConnection
from database.models import AppSetting, Base, Lead, LeadSequence, User
from database.schema_manager import ensure_assignment_integrity, ensure_column_defaults, ensure_phase2_schema, ensure_phase3_schema, ensure_phase4_schema, ensure_phase5_data_cleanup
from modules.dropdown_config import sync_dropdowns_from_workbook
from modules.logger import setup_logger
from modules.mysql_sync import MySQLSyncEngine


RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
BACKUP_DIR = PROJECT_ROOT / "data" / "backup"
SQLITE_DB = PROJECT_ROOT / "database" / "sales_leads.db"
EXCEL_EXTENSIONS = (".xlsx", ".xlsm")
ProgressCallback = Callable[[str, str], None]


@dataclass
class StartupStatus:
    """Status report shown in Streamlit during startup."""

    mysql_connected: bool = False
    tables_loaded: bool = False
    excel_synced: bool = False
    dashboard_ready: bool = False
    imported_file: str | None = None
    lead_count: int = 0
    messages: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def initialize_crm(db: DatabaseConnection, progress: ProgressCallback | None = None, force_sync: bool = False) -> StartupStatus:
    """Prepare MySQL, sync Excel when needed, and return dashboard readiness."""
    logger = setup_logger(LOG_DIR)
    status = StartupStatus()

    try:
        _emit(progress, "MySQL Connected", "Checking MySQL connection")
        db.ensure_database_exists()
        if not db.health_check():
            raise RuntimeError(db.last_error_message or "MySQL health check failed")
        status.mysql_connected = True

        _emit(progress, "Tables Loaded", "Creating or upgrading CRM tables")
        Base.metadata.create_all(db.engine)
        ensure_phase2_schema(db.engine)
        ensure_phase3_schema(db.engine)
        ensure_phase4_schema(db.engine)
        ensure_phase5_data_cleanup(db.engine)
        ensure_assignment_integrity(db.engine)
        ensure_column_defaults(db.engine)
        _ensure_default_admin(db)
        status.tables_loaded = _required_tables_exist(db)
        if not status.tables_loaded:
            raise RuntimeError("Required CRM tables are missing after schema initialization.")

        _emit(progress, "Excel Synced", "Checking current database and Excel source")
        lead_count = _lead_count(db)
        source_file, source_kind = _find_sync_source()
        dropdown_source = _find_dropdown_source(source_file)
        if dropdown_source:
            sync_dropdowns_from_workbook(dropdown_source)
            status.messages.append(f"Dropdown values synchronized from {dropdown_source.name}.")
        # Also force sync when lead count looks stale (< 200) vs known Google Sheet size
        should_sync = force_sync or lead_count == 0 or lead_count < 200 or _source_changed(db, source_file)

        if should_sync and source_file:
            if lead_count == 0:
                status.messages.append("Database empty. Importing Excel data...")
            cleaned_file = _prepare_cleaned_file(source_file, source_kind)
            summary = MySQLSyncEngine(db, logger).import_cleaned_excel(cleaned_file, user_name="startup")
            _update_sequence_from_import(db)
            _set_sync_setting(db, source_file)
            status.imported_file = str(cleaned_file)
            status.messages.append(
                f"Excel sync completed: {summary.inserted_rows} inserted, {summary.updated_rows} updated, "
                f"{summary.skipped_rows} skipped, {summary.failed_rows} failed."
            )
        elif source_file:
            status.messages.append("Excel source already synchronized.")
        else:
            status.messages.append("No Excel workbook found in data/raw or data/processed.")

        # Recompute lead scores for every lead (imported leads start at 0.0).
        try:
            from modules.lead_scoring import recompute_all_scores
            with db.session_scope() as session:
                updated = recompute_all_scores(session)
            if updated:
                status.messages.append(f"Lead scores recomputed for {updated} leads.")
        except Exception as exc:  # never block dashboard on scoring
            logger.warning("Lead score recompute skipped: %s", exc)

        status.lead_count = _lead_count(db)
        status.excel_synced = bool(status.lead_count) or source_file is None
        status.dashboard_ready = status.mysql_connected and status.tables_loaded
        if status.dashboard_ready:
            status.messages.append("Dashboard synchronized successfully.")
        logger.info("CRM startup completed: %s", status)
        return status
    except Exception as exc:
        message = _format_startup_error(db, exc)
        status.errors.append(message)
        logger.exception("CRM startup failed: %s", message)
        return status


def _emit(progress: ProgressCallback | None, label: str, detail: str) -> None:
    if progress:
        progress(label, detail)


def _ensure_default_admin(db: DatabaseConnection) -> None:
    import os

    username = os.getenv("CRM_ADMIN_USER", "admin")
    password = os.getenv("CRM_ADMIN_PASSWORD", "admin123")
    with db.session_scope() as session:
        has_user = session.scalar(select(User.user_id).limit(1))
        if has_user:
            return
        session.add(
            User(
                username=username,
                password_hash=hash_password(password),
                full_name="System Admin",
                role="Admin",
                is_active=True,
            )
        )


def _required_tables_exist(db: DatabaseConnection) -> bool:
    required = {"leads", "followups", "activity_logs", "duplicate_reports", "users", "app_settings", "lead_sequences"}
    return required.issubset(set(inspect(db.engine).get_table_names()))


def _lead_count(db: DatabaseConnection) -> int:
    with db.session_scope() as session:
        return session.scalar(select(func.count()).select_from(Lead).where(Lead.deleted_at.is_(None))) or 0


def _find_sync_source() -> tuple[Path | None, str | None]:
    raw_files = _latest_files(RAW_DIR, EXCEL_EXTENSIONS)
    if raw_files:
        return raw_files[0], "raw"

    # Also treat the latest Google Sheet backup as a raw source when available
    backup_sheets = sorted(BACKUP_DIR.glob("google_sheet_latest_*.xlsx"), key=lambda path: path.stat().st_mtime, reverse=True)
    if backup_sheets:
        return backup_sheets[0], "raw"

    cleaned_files = sorted(PROCESSED_DIR.glob("*/cleaned_sales_leads.xlsx"), key=lambda path: path.stat().st_mtime, reverse=True)
    if cleaned_files:
        return cleaned_files[0], "processed"
    return None, None


def _find_dropdown_source(source_file: Path | None) -> Path | None:
    # Prefer the latest Google Sheet backup for dropdowns (most up-to-date validations)
    candidates = sorted(BACKUP_DIR.glob("google_sheet_latest_*.xlsx"), key=lambda path: path.stat().st_mtime, reverse=True)
    if candidates:
        return candidates[0]
    # Fall back to the raw source file if it's a real workbook (not a cleaned artifact)
    if source_file and source_file.suffix.lower() in EXCEL_EXTENSIONS and "cleaned_sales_leads" not in source_file.name:
        return source_file
    return None


def _latest_files(directory: Path, extensions: tuple[str, ...]) -> list[Path]:
    if not directory.exists():
        return []
    return sorted(
        [path for path in directory.iterdir() if path.is_file() and path.suffix.lower() in extensions and not path.name.startswith("~$")],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )


def _source_changed(db: DatabaseConnection, source_file: Path | None) -> bool:
    if source_file is None:
        return False
    with db.session_scope() as session:
        stored_path = session.get(AppSetting, "excel_sync_source")
        stored_mtime = session.get(AppSetting, "excel_sync_mtime")
        current_mtime = str(source_file.stat().st_mtime)
        return (
            stored_path is None
            or stored_mtime is None
            or stored_path.setting_value != str(source_file)
            or stored_mtime.setting_value != current_mtime
        )


def _prepare_cleaned_file(source_file: Path, source_kind: str | None) -> Path:
    if source_kind == "processed":
        return source_file

    from main import run_preprocessing

    before = set(PROCESSED_DIR.glob("*/cleaned_sales_leads.xlsx"))
    args = SimpleNamespace(input=str(source_file), db=str(SQLITE_DB), year=datetime.now().year, threshold=None)
    run_preprocessing(args)
    after = set(PROCESSED_DIR.glob("*/cleaned_sales_leads.xlsx"))
    new_files = sorted(after - before, key=lambda path: path.stat().st_mtime, reverse=True)
    if new_files:
        return new_files[0]
    cleaned_files = sorted(after, key=lambda path: path.stat().st_mtime, reverse=True)
    if not cleaned_files:
        raise FileNotFoundError("Preprocessing completed without producing cleaned_sales_leads.xlsx")
    return cleaned_files[0]


def _set_sync_setting(db: DatabaseConnection, source_file: Path) -> None:
    values = {
        "excel_sync_source": str(source_file),
        "excel_sync_mtime": str(source_file.stat().st_mtime),
        "excel_sync_completed_at": datetime.now().isoformat(timespec="seconds"),
    }
    with db.session_scope() as session:
        for key, value in values.items():
            setting = session.get(AppSetting, key)
            if setting is None:
                session.add(AppSetting(setting_key=key, setting_value=value))
            else:
                setting.setting_value = value


def _update_sequence_from_import(db: DatabaseConnection) -> None:
    pattern = re.compile(r"^FT-(\d{4})-(\d+)$")
    highest: dict[int, int] = {}
    with db.session_scope() as session:
        for lead_id in session.scalars(select(Lead.lead_id)):
            match = pattern.match(str(lead_id))
            if not match:
                continue
            year = int(match.group(1))
            number = int(match.group(2))
            highest[year] = max(highest.get(year, 0), number)
        for year, number in highest.items():
            sequence = session.get(LeadSequence, year)
            if sequence is None:
                session.add(LeadSequence(year=year, last_number=number))
            else:
                sequence.last_number = max(sequence.last_number, number)


def _format_startup_error(db: DatabaseConnection, exc: Exception) -> str:
    if isinstance(exc, SQLAlchemyError):
        return db.format_connection_error(exc)
    return str(exc)
