"""CLI entry point for Phase 1 sales lead preprocessing."""

from __future__ import annotations

import argparse
import json
import shutil
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from modules.cleaner import DataCleaner
from modules.database_manager import DatabaseManager
from modules.duplicate_detector import DuplicateDetector
from modules.logger import setup_logger
from modules.transformer import DataTransformer
from modules.validator import DataValidator


PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
BACKUP_DIR = DATA_DIR / "backup"
LOG_DIR = PROJECT_ROOT / "logs"
CONFIG_DIR = PROJECT_ROOT / "config"
DATABASE_DIR = PROJECT_ROOT / "database"


@dataclass
class PreprocessingSummary:
    """Summary metrics for one preprocessing run."""

    run_id: str
    input_file: str
    total_sheets_read: int
    missing_expected_sheets: list[str]
    total_rows_processed: int
    cleaned_rows: int
    invalid_rows: int
    duplicates_found: int
    missing_values: int
    data_quality_score: float
    processing_time_seconds: float
    cleaned_excel_path: str
    cleaned_csv_path: str
    duplicate_report_path: str
    validation_report_path: str
    database_path: str


class ExcelIngestion:
    """Read workbooks, normalize sheet names, and create raw backups."""

    EXPECTED_SHEETS = ["Buyer_Master", "Follow_Up", "Alibaba"]

    def __init__(self, cleaner: DataCleaner, logger) -> None:
        self.cleaner = cleaner
        self.logger = logger

    def backup_input(self, input_path: Path, run_id: str) -> Path:
        """Copy the original workbook into the backup directory."""
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        backup_path = BACKUP_DIR / f"{input_path.stem}_{run_id}{input_path.suffix}"
        shutil.copy2(input_path, backup_path)
        self.logger.info("Raw backup saved to %s", backup_path)
        return backup_path

    def read_workbook(self, input_path: Path) -> tuple[dict[str, pd.DataFrame], list[str]]:
        """Read all workbook sheets and clean their column names."""
        try:
            workbook = pd.ExcelFile(input_path, engine="openpyxl")
        except Exception as exc:
            self.logger.exception("Could not open workbook: %s", input_path)
            raise RuntimeError(f"Could not open workbook '{input_path}': {exc}") from exc

        missing = [sheet for sheet in self.EXPECTED_SHEETS if sheet not in workbook.sheet_names]
        for sheet in missing:
            self.logger.warning("Expected sheet is missing: %s", sheet)

        sheets: dict[str, pd.DataFrame] = {}
        for sheet_name in workbook.sheet_names:
            try:
                df = pd.read_excel(workbook, sheet_name=sheet_name, dtype=object)
                df = self.cleaner.clean_dataframe(df)
                sheets[sheet_name.strip()] = df
                self.logger.info("Read sheet '%s' with %s rows", sheet_name, len(df))
            except Exception:
                self.logger.exception("Failed to read sheet '%s'; skipping", sheet_name)
        return sheets, missing


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="Sales Lead Automation backend CLI.")
    parser.add_argument("--input", help="Backward-compatible raw Excel input for preprocessing")
    parser.add_argument("--db", default=str(DATABASE_DIR / "sales_leads.db"), help="SQLite database path for preprocessing")
    parser.add_argument("--year", type=int, default=datetime.now().year, help="Lead ID year, e.g. 2026")
    parser.add_argument("--threshold", type=int, default=None, help="Duplicate similarity threshold")

    subparsers = parser.add_subparsers(dest="command")

    preprocess = subparsers.add_parser("preprocess", help="Clean raw Excel and write Phase 1 artifacts")
    preprocess.add_argument("--input", required=True, help="Path to raw Excel workbook")
    preprocess.add_argument("--db", default=str(DATABASE_DIR / "sales_leads.db"), help="SQLite database path")
    preprocess.add_argument("--year", type=int, default=datetime.now().year)
    preprocess.add_argument("--threshold", type=int, default=None)

    subparsers.add_parser("init-mysql", help="Create MySQL tables using SQLAlchemy models")

    health = subparsers.add_parser("healthcheck-mysql", help="Check configured MySQL connectivity")
    health.set_defaults(command="healthcheck-mysql")

    import_mysql = subparsers.add_parser("import-mysql", help="Import cleaned Phase 1 workbook into MySQL")
    import_mysql.add_argument("--cleaned-file", required=True, help="Path to cleaned_sales_leads.xlsx or clean_leads.csv")
    import_mysql.add_argument("--user", default="system", help="User name for audit logs")

    sync_mysql = subparsers.add_parser("sync-mysql", help="Alias for import-mysql with update/skip behavior")
    sync_mysql.add_argument("--cleaned-file", required=True, help="Path to cleaned_sales_leads.xlsx or clean_leads.csv")
    sync_mysql.add_argument("--user", default="system", help="User name for audit logs")

    export_mysql = subparsers.add_parser("export-mysql", help="Export MySQL CRM tables")
    export_mysql.add_argument("--output-dir", default=None, help="Optional export directory")
    return parser.parse_args()


def load_validation_config() -> dict[str, Any]:
    """Load validation JSON for orchestration settings."""
    with (CONFIG_DIR / "validation_rules.json").open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_outputs(
    run_id: str,
    leads: pd.DataFrame,
    followups: pd.DataFrame,
    orders: pd.DataFrame,
    duplicates: pd.DataFrame,
    validation_report: pd.DataFrame,
    summary: PreprocessingSummary,
) -> None:
    """Persist cleaned datasets and reports."""
    run_dir = PROCESSED_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(run_dir / "cleaned_sales_leads.xlsx", engine="openpyxl") as writer:
        leads.to_excel(writer, sheet_name="clean_leads", index=False)
        followups.to_excel(writer, sheet_name="clean_followups", index=False)
        orders.to_excel(writer, sheet_name="clean_orders", index=False)
        duplicates.to_excel(writer, sheet_name="duplicate_report", index=False)
        validation_report.to_excel(writer, sheet_name="validation_report", index=False)
        pd.DataFrame([asdict(summary)]).to_excel(writer, sheet_name="summary", index=False)

    leads.to_csv(run_dir / "clean_leads.csv", index=False)
    followups.to_csv(run_dir / "clean_followups.csv", index=False)
    orders.to_csv(run_dir / "clean_orders.csv", index=False)
    duplicates.to_csv(run_dir / "duplicate_report.csv", index=False)
    validation_report.to_csv(run_dir / "validation_report.csv", index=False)

    with (run_dir / "preprocessing_summary.json").open("w", encoding="utf-8") as handle:
        json.dump(asdict(summary), handle, indent=2)


def calculate_quality_score(total_rows: int, invalid_rows: int, duplicates_found: int, missing_values: int) -> float:
    """Calculate a simple 0-100 data quality score."""
    if total_rows == 0:
        return 0.0
    invalid_penalty = invalid_rows / total_rows * 45
    duplicate_penalty = min(duplicates_found / max(total_rows, 1) * 25, 25)
    missing_penalty = min(missing_values / max(total_rows * 10, 1) * 30, 30)
    return round(max(0.0, 100 - invalid_penalty - duplicate_penalty - missing_penalty), 2)


def run_preprocessing(args: argparse.Namespace) -> None:
    """Run the full preprocessing workflow."""
    started = time.perf_counter()
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    input_path = Path(args.input).expanduser().resolve()
    if not input_path.is_file():
        raise SystemExit(
            f"Input workbook not found: {input_path}\n"
            "Pass the full Excel file path with --input, for example:\n"
            'python main.py preprocess --input "C:\\path\\to\\Sales_Master_Tracker.xlsx"'
        )

    logger = setup_logger(LOG_DIR)
    logger.info("Starting preprocessing run %s", run_id)

    cleaner = DataCleaner(CONFIG_DIR / "status_mapping.json", logger)
    ingestion = ExcelIngestion(cleaner, logger)
    validator = DataValidator(CONFIG_DIR / "validation_rules.json", logger)
    validation_config = load_validation_config()
    threshold = args.threshold or int(validation_config.get("duplicate_similarity_threshold", 88))
    duplicate_detector = DuplicateDetector(threshold, logger)
    transformer = DataTransformer(logger)
    database = DatabaseManager(Path(args.db), logger)

    ingestion.backup_input(input_path, run_id)
    sheets, missing_sheets = ingestion.read_workbook(input_path)
    raw_rows = sum(len(df) for df in sheets.values())

    leads = transformer.build_leads(sheets)
    leads = database.assign_lead_ids(leads, args.year)
    valid_leads, validation_report = validator.validate_leads(leads)
    duplicates = duplicate_detector.find_duplicates(valid_leads)
    followups = transformer.build_followups(sheets, valid_leads)
    orders = transformer.build_orders(sheets, valid_leads)

    database.insert_leads(valid_leads)
    database.insert_followups(followups)
    database.insert_orders(orders)

    run_dir = PROCESSED_DIR / run_id
    summary = PreprocessingSummary(
        run_id=run_id,
        input_file=str(input_path),
        total_sheets_read=len(sheets),
        missing_expected_sheets=missing_sheets,
        total_rows_processed=raw_rows,
        cleaned_rows=len(valid_leads),
        invalid_rows=len(validation_report),
        duplicates_found=len(duplicates),
        missing_values=int(valid_leads.isna().sum().sum()) if not valid_leads.empty else 0,
        data_quality_score=calculate_quality_score(
            raw_rows,
            len(validation_report),
            len(duplicates),
            int(valid_leads.isna().sum().sum()) if not valid_leads.empty else 0,
        ),
        processing_time_seconds=round(time.perf_counter() - started, 2),
        cleaned_excel_path=str(run_dir / "cleaned_sales_leads.xlsx"),
        cleaned_csv_path=str(run_dir / "clean_leads.csv"),
        duplicate_report_path=str(run_dir / "duplicate_report.csv"),
        validation_report_path=str(run_dir / "validation_report.csv"),
        database_path=str(Path(args.db).resolve()),
    )

    write_outputs(run_id, valid_leads, followups, orders, duplicates, validation_report, summary)
    logger.info("Preprocessing complete: %s", json.dumps(asdict(summary), indent=2))
    print(json.dumps(asdict(summary), indent=2))


def run_mysql_init() -> None:
    """Initialize MySQL schema."""
    from database.db_connection import DatabaseConnection
    from database.models import Base
    from database.schema_manager import ensure_assignment_integrity, ensure_column_defaults, ensure_phase2_schema, ensure_phase3_schema, ensure_phase4_schema, ensure_phase5_data_cleanup
    from sqlalchemy.exc import SQLAlchemyError

    logger = setup_logger(LOG_DIR)
    connection = DatabaseConnection(logger=logger)
    try:
        connection.ensure_database_exists()
        Base.metadata.create_all(connection.engine)
        ensure_phase2_schema(connection.engine)
        ensure_phase3_schema(connection.engine)
        ensure_phase4_schema(connection.engine)
        ensure_phase5_data_cleanup(connection.engine)
        ensure_assignment_integrity(connection.engine)
        ensure_column_defaults(connection.engine)
    except SQLAlchemyError as exc:
        message = connection.format_connection_error(exc)
        logger.error("MySQL schema initialization failed: %s", message)
        raise SystemExit(message) from exc
    logger.info("MySQL schema initialized")
    print("MySQL schema initialized successfully.")


def run_mysql_healthcheck() -> None:
    """Check MySQL connectivity."""
    from database.db_connection import DatabaseConnection

    logger = setup_logger(LOG_DIR)
    connection = DatabaseConnection(logger=logger)
    ok = connection.health_check()
    if ok:
        print("MySQL health check: OK")
    else:
        print(f"MySQL health check: FAILED\n{connection.last_error_message}")


def run_mysql_import(args: argparse.Namespace) -> None:
    """Run cleaned Excel to MySQL import/sync."""
    from database.db_connection import DatabaseConnection
    from modules.mysql_sync import MySQLSyncEngine
    from sqlalchemy.exc import SQLAlchemyError

    logger = setup_logger(LOG_DIR)
    connection = DatabaseConnection(logger=logger)
    engine = MySQLSyncEngine(connection, logger)
    try:
        summary = engine.import_cleaned_excel(Path(args.cleaned_file).expanduser().resolve(), user_name=args.user)
    except SQLAlchemyError as exc:
        message = connection.format_connection_error(exc)
        logger.error("MySQL import failed: %s", message)
        raise SystemExit(message) from exc
    print(json.dumps(asdict(summary), indent=2, default=str))


def run_mysql_export(args: argparse.Namespace) -> None:
    """Export MySQL tables."""
    from database.db_connection import DatabaseConnection
    from modules.mysql_sync import MySQLSyncEngine
    from sqlalchemy.exc import SQLAlchemyError

    logger = setup_logger(LOG_DIR)
    connection = DatabaseConnection(logger=logger)
    engine = MySQLSyncEngine(connection, logger)
    output_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else None
    try:
        outputs = engine.export_all(output_dir)
    except SQLAlchemyError as exc:
        message = connection.format_connection_error(exc)
        logger.error("MySQL export failed: %s", message)
        raise SystemExit(message) from exc
    print(json.dumps(outputs, indent=2))


def main() -> None:
    """Route CLI commands."""
    args = parse_args()
    command = args.command or ("preprocess" if args.input else None)
    if command == "preprocess":
        run_preprocessing(args)
    elif command == "init-mysql":
        run_mysql_init()
    elif command == "healthcheck-mysql":
        run_mysql_healthcheck()
    elif command in {"import-mysql", "sync-mysql"}:
        run_mysql_import(args)
    elif command == "export-mysql":
        run_mysql_export(args)
    else:
        raise SystemExit("Choose a command or provide --input for preprocessing. Use --help for options.")


if __name__ == "__main__":
    main()
