"""SQLite persistence layer for cleaned CRM data."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

import pandas as pd


class DatabaseManager:
    """Manage SQLite schema, lead IDs, and cleaned data inserts."""

    def __init__(self, db_path: Path, logger: logging.Logger) -> None:
        self.db_path = db_path
        self.logger = logger
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize_schema()

    def connect(self) -> sqlite3.Connection:
        """Open a SQLite connection."""
        return sqlite3.connect(self.db_path)

    def initialize_schema(self) -> None:
        """Create CRM tables and sequence table."""
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS lead_sequence (
                    year INTEGER PRIMARY KEY,
                    last_number INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS leads (
                    lead_id TEXT PRIMARY KEY,
                    legacy_buyer_id TEXT,
                    buyer_tag TEXT,
                    company_name TEXT,
                    website TEXT,
                    industry TEXT,
                    city TEXT,
                    continent TEXT,
                    contact_person TEXT,
                    designation TEXT,
                    phone TEXT,
                    alternate_number TEXT,
                    whatsapp_number TEXT,
                    email TEXT,
                    country TEXT,
                    status TEXT,
                    assigned_to TEXT,
                    transfer_to TEXT,
                    lead_source TEXT,
                    product_interest TEXT,
                    probability TEXT,
                    follow_up_stage TEXT,
                    mode TEXT,
                    quotation_status TEXT,
                    remarks TEXT,
                    procurement_remarks TEXT,
                    internal_notes TEXT,
                    created_date TEXT,
                    last_contact_date TEXT,
                    first_contact_date TEXT,
                    next_follow_up TEXT,
                    sheet_source TEXT
                );

                CREATE TABLE IF NOT EXISTS followups (
                    followup_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lead_id TEXT,
                    legacy_buyer_id TEXT,
                    buyer_name TEXT,
                    country TEXT,
                    assigned_to TEXT,
                    transfer_to TEXT,
                    followup_date TEXT,
                    discussion TEXT,
                    next_action TEXT,
                    next_followup TEXT,
                    mode TEXT,
                    status TEXT,
                    updated_by TEXT,
                    FOREIGN KEY (lead_id) REFERENCES leads (lead_id)
                );

                CREATE TABLE IF NOT EXISTS order_tracker (
                    order_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lead_id TEXT,
                    legacy_buyer_id TEXT,
                    buyer_name TEXT,
                    product TEXT,
                    category TEXT,
                    quantity TEXT,
                    order_value TEXT,
                    currency TEXT,
                    order_date TEXT,
                    dispatch_date TEXT,
                    payment_terms TEXT,
                    payment_status TEXT,
                    order_status TEXT,
                    handled_by TEXT,
                    FOREIGN KEY (lead_id) REFERENCES leads (lead_id)
                );

                CREATE TABLE IF NOT EXISTS activity_logs (
                    timestamp TEXT,
                    action TEXT,
                    user TEXT,
                    lead_id TEXT
                );
                """
            )
            self._ensure_columns(
                connection,
                "leads",
                {
                    "legacy_buyer_id": "TEXT",
                    "buyer_tag": "TEXT",
                    "website": "TEXT",
                    "industry": "TEXT",
                    "city": "TEXT",
                    "continent": "TEXT",
                    "designation": "TEXT",
                    "alternate_number": "TEXT",
                    "whatsapp_number": "TEXT",
                    "transfer_to": "TEXT",
                    "product_interest": "TEXT",
                    "probability": "TEXT",
                    "follow_up_stage": "TEXT",
                    "mode": "TEXT",
                    "quotation_status": "TEXT",
                    "remarks": "TEXT",
                    "procurement_remarks": "TEXT",
                    "internal_notes": "TEXT",
                    "last_contact_date": "TEXT",
                    "first_contact_date": "TEXT",
                    "next_follow_up": "TEXT",
                    "sheet_source": "TEXT",
                },
            )
            self._ensure_columns(
                connection,
                "followups",
                {
                    "legacy_buyer_id": "TEXT",
                    "buyer_name": "TEXT",
                    "country": "TEXT",
                    "assigned_to": "TEXT",
                    "transfer_to": "TEXT",
                    "mode": "TEXT",
                    "status": "TEXT",
                },
            )
        self.logger.info("SQLite schema initialized at %s", self.db_path)

    @staticmethod
    def _ensure_columns(connection: sqlite3.Connection, table: str, columns: dict[str, str]) -> None:
        existing = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
        for column, column_type in columns.items():
            if column not in existing:
                connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")

    def assign_lead_ids(self, leads: pd.DataFrame, year: int) -> pd.DataFrame:
        """Assign stable FT-YYYY-NNNN lead IDs — reuses existing ID for same legacy_buyer_id."""
        output = leads.copy()
        if "lead_id" not in output.columns:
            output.insert(0, "lead_id", None)

        # Build lookup: legacy_buyer_id -> existing lead_id from DB (idempotency)
        existing_map: dict[str, str] = {}
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT legacy_buyer_id, lead_id FROM leads WHERE legacy_buyer_id IS NOT NULL"
            ).fetchall()
            existing_map = {r[0]: r[1] for r in rows}

        # Reuse existing IDs where legacy_buyer_id already has one
        if "legacy_buyer_id" in output.columns:
            for idx, row in output.iterrows():
                lid = row.get("legacy_buyer_id")
                if lid and lid in existing_map and (pd.isna(row.get("lead_id")) or str(row.get("lead_id")).strip() == ""):
                    output.at[idx, "lead_id"] = existing_map[lid]

        missing_mask = output["lead_id"].isna() | (output["lead_id"].astype(str).str.strip() == "")
        count = int(missing_mask.sum())
        if count == 0:
            return output

        with self.connect() as connection:
            current = connection.execute(
                "SELECT last_number FROM lead_sequence WHERE year = ?", (year,)
            ).fetchone()
            last_number = int(current[0]) if current else 0
            new_ids = [f"FT-{year}-{number:04d}" for number in range(last_number + 1, last_number + count + 1)]
            output.loc[missing_mask, "lead_id"] = new_ids
            connection.execute(
                """
                INSERT INTO lead_sequence (year, last_number) VALUES (?, ?)
                ON CONFLICT(year) DO UPDATE SET last_number = excluded.last_number
                """,
                (year, last_number + count),
            )
        self.logger.info("Assigned %s new lead IDs, reused %s existing", count, len(existing_map))
        return output

    def insert_leads(self, leads: pd.DataFrame) -> None:
        """Upsert leads into SQLite."""
        columns = [
            "lead_id", "legacy_buyer_id", "buyer_tag", "company_name", "website",
            "industry", "city", "continent", "contact_person", "designation",
            "phone", "alternate_number", "whatsapp_number", "email", "country",
            "status", "assigned_to", "transfer_to", "lead_source", "product_interest",
            "probability", "follow_up_stage", "mode", "quotation_status",
            "remarks", "procurement_remarks", "internal_notes",
            "created_date", "last_contact_date", "first_contact_date", "next_follow_up", "sheet_source",
        ]
        payload = leads.reindex(columns=columns)
        col_list = ", ".join(columns)
        with self.connect() as connection:
            payload.to_sql("_leads_stage", connection, if_exists="replace", index=False)
            connection.execute(
                f"""
                INSERT OR REPLACE INTO leads ({col_list})
                SELECT {col_list} FROM _leads_stage WHERE lead_id IS NOT NULL
                """
            )
            connection.execute("DROP TABLE _leads_stage")
        self.logger.info("Inserted/upserted %s leads", len(payload))

    def insert_followups(self, followups: pd.DataFrame) -> None:
        """Append follow-up rows into SQLite."""
        if followups.empty:
            return
        columns = [
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
        payload = followups.reindex(columns=columns)
        with self.connect() as connection:
            payload.to_sql("followups", connection, if_exists="append", index=False)
        self.logger.info("Inserted %s followups", len(payload))

    def insert_orders(self, orders: pd.DataFrame) -> None:
        """Append order tracker rows into SQLite."""
        if orders.empty:
            return
        columns = [
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
        payload = orders.reindex(columns=columns)
        with self.connect() as connection:
            payload.to_sql("order_tracker", connection, if_exists="append", index=False)
        self.logger.info("Inserted %s order rows", len(payload))
