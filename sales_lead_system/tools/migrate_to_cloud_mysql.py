"""One-time data migration: local MySQL  ->  cloud MySQL (Aiven/Railway/etc.).

Reads from your LOCAL database (config/.env) and copies every row into the
TARGET cloud database. The target schema is created automatically (same
migrations the app runs on startup), so the cloud DB can start empty.

Usage (from the sales_lead_system folder):

    .venv_codex\\Scripts\\python.exe tools\\migrate_to_cloud_mysql.py ^
        --target "mysql+mysqlconnector://USER:PASS@HOST:PORT/DBNAME?charset=utf8mb4&ssl_disabled=false"

Nothing is deleted from the local database. Safe to re-run (target tables are
refilled). Use --dry-run to preview counts without writing.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from config.settings import get_mysql_settings
from database.models import Base
from database.schema_manager import (
    ensure_assignment_integrity, ensure_column_defaults, ensure_phase2_schema,
    ensure_phase3_schema, ensure_phase4_schema, ensure_phase5_data_cleanup,
)

# FK-safe insertion order (parents before children).
TABLE_ORDER = [
    "users", "app_settings", "lead_sequences",
    "leads", "followups", "engagement_events",
    "activity_logs", "order_tracker", "duplicate_reports",
]


def _prepare_target(engine: Engine) -> None:
    """Create all tables + run the same migrations the app runs on startup."""
    Base.metadata.create_all(engine)
    for fn in (ensure_phase2_schema, ensure_phase3_schema, ensure_phase4_schema):
        try:
            fn(engine)
        except Exception as exc:  # phase migrations are best-effort on a fresh DB
            print(f"  (skip {fn.__name__}: {exc})")


def _copy_table(src: Engine, dst: Engine, table: str, dry_run: bool) -> int:
    with src.connect() as s:
        try:
            rows = [dict(r._mapping) for r in s.execute(text(f"SELECT * FROM {table}"))]
        except Exception:
            return 0  # table may not exist in source
    if not rows:
        print(f"  {table}: 0 rows")
        return 0
    if dry_run:
        print(f"  {table}: {len(rows)} rows (dry-run, not written)")
        return len(rows)
    cols = list(rows[0].keys())
    collist = ", ".join(f"`{c}`" for c in cols)
    params = ", ".join(f":{c}" for c in cols)
    with dst.begin() as d:
        d.execute(text("SET FOREIGN_KEY_CHECKS=0"))
        d.execute(text(f"DELETE FROM {table}"))
        d.execute(text(f"INSERT INTO {table} ({collist}) VALUES ({params})"), rows)
        d.execute(text("SET FOREIGN_KEY_CHECKS=1"))
    print(f"  {table}: {len(rows)} rows copied")
    return len(rows)


def _build_target_url(args) -> str:
    """Build a safe SQLAlchemy URL from --target, or from separate parts."""
    if args.target:
        return args.target
    from urllib.parse import quote_plus
    import os
    pw = args.password or os.getenv("CLOUD_DB_PASSWORD", "")
    user = quote_plus(args.user)
    pw = quote_plus(pw)
    host = quote_plus(args.host)
    db = quote_plus(args.database)
    ssl = "&ssl_disabled=false" if args.ssl else ""
    return f"mysql+mysqlconnector://{user}:{pw}@{host}:{args.port}/{db}?charset=utf8mb4{ssl}"


def main() -> None:
    ap = argparse.ArgumentParser(description="Migrate local MySQL data to a cloud MySQL.")
    ap.add_argument("--target", help="Full SQLAlchemy URL of the CLOUD MySQL (alternative to parts below)")
    ap.add_argument("--host", help="Cloud MySQL host")
    ap.add_argument("--port", type=int, default=3306, help="Cloud MySQL port")
    ap.add_argument("--user", help="Cloud MySQL user")
    ap.add_argument("--password", help="Cloud MySQL password (or set CLOUD_DB_PASSWORD env var)")
    ap.add_argument("--database", help="Cloud MySQL database name")
    ap.add_argument("--ssl", action="store_true", help="Use TLS (required by most hosts like Aiven)")
    ap.add_argument("--dry-run", action="store_true", help="Preview counts only, no writes")
    args = ap.parse_args()

    if not args.target and not (args.host and args.user and args.database):
        ap.error("Provide either --target URL, or --host --user --database (+ --password).")

    target_url = _build_target_url(args)
    src = create_engine(get_mysql_settings().sqlalchemy_url, pool_pre_ping=True)
    dst = create_engine(target_url, pool_pre_ping=True)

    print("Source (local):", get_mysql_settings().redacted_dsn)
    print("Target (cloud):", target_url.split("@")[-1])
    print()

    if not args.dry_run:
        print("Preparing target schema...")
        _prepare_target(dst)

    print("Copying tables:")
    total = sum(_copy_table(src, dst, t, args.dry_run) for t in TABLE_ORDER)

    if not args.dry_run:
        print("Running integrity + cleanup on target...")
        for fn in (ensure_phase5_data_cleanup, ensure_assignment_integrity, ensure_column_defaults):
            try:
                fn(dst)
            except Exception as exc:
                print(f"  (skip {fn.__name__}: {exc})")

    print(f"\nDone. {total} total rows {'previewed' if args.dry_run else 'migrated'}.")


if __name__ == "__main__":
    main()
