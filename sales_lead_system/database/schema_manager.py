"""Idempotent schema upgrades — MySQL + SQLite compatible.

All operations are guarded (check then apply) and safe to re-run.
SQLite: ADD COLUMN DDL works (one column per ALTER TABLE);
       MODIFY COLUMN, TINYINT, SHOW INDEX, FK constraints are MySQL-only.
"""

from __future__ import annotations

from sqlalchemy import bindparam, inspect, text
from sqlalchemy.engine import Engine


# ── Helpers ───────────────────────────────────────────────────────────────────

def _is_mysql(engine: Engine) -> bool:
    return engine.dialect.name == "mysql"


def _needed_columns(engine: Engine, table: str) -> set[str]:
    if table not in set(inspect(engine).get_table_names()):
        return set()
    return {col["name"] for col in inspect(engine).get_columns(table)}


def _add_missing_columns(engine: Engine, table: str, column_defs: dict[str, str]) -> None:
    """Add only columns that don't exist yet."""
    existing = _needed_columns(engine, table)
    to_add = [(col_name, col_def) for col_name, col_def in column_defs.items() if col_name not in existing]
    if not to_add:
        return
    if _is_mysql(engine):
        sql = "ALTER TABLE " + table + " " + ", ".join(f"ADD COLUMN {col}" for _, col in to_add)
        with engine.begin() as conn:
            conn.execute(text(sql))
    else:
        for _, col_def in to_add:
            sql = f"ALTER TABLE {table} ADD COLUMN {col_def}"
            try:
                with engine.begin() as conn:
                    conn.execute(text(sql))
            except Exception:
                # SQLite may reject DEFAULT with non-constant expression
                # Strip DEFAULT clause and retry
                import re
                stripped = re.sub(r"\s+DEFAULT\s+[^\s,)]+", "", col_def, flags=re.IGNORECASE)
                if stripped != col_def:
                    sql = f"ALTER TABLE {table} ADD COLUMN {stripped}"
                    with engine.begin() as conn:
                        conn.execute(text(sql))
                else:
                    raise


def _missing_index(engine: Engine, table: str, index_name: str) -> bool:
    if table not in set(inspect(engine).get_table_names()):
        return False
    return index_name not in {ix["name"] for ix in inspect(engine).get_indexes(table)}


# ── Column definitions ────────────────────────────────────────────────────────

PHASE2_LEAD_COLUMNS = {
    "legacy_buyer_id": "legacy_buyer_id VARCHAR(50) NULL",
    "buyer_tag": "buyer_tag VARCHAR(20) NULL",
    "website": "website VARCHAR(255) NULL",
    "industry": "industry VARCHAR(120) NULL",
    "city": "city VARCHAR(120) NULL",
    "designation": "designation VARCHAR(120) NULL",
    "alternate_number": "alternate_number VARCHAR(50) NULL",
    "whatsapp_number": "whatsapp_number VARCHAR(50) NULL",
    "continent": "continent VARCHAR(100) NULL",
    "transfer_to": "transfer_to VARCHAR(100) NULL",
    "product_interest": "product_interest VARCHAR(255) NULL",
    "probability": "probability VARCHAR(20) NULL",
    "follow_up_stage": "follow_up_stage VARCHAR(50) NULL",
    "mode": "mode VARCHAR(50) NULL",
    "quotation_status": "quotation_status VARCHAR(50) NULL",
    "moq_requirement": "moq_requirement VARCHAR(100) NULL",
    "expected_quantity": "expected_quantity VARCHAR(100) NULL",
    "budget_range": "budget_range VARCHAR(100) NULL",
    "priority_level": "priority_level VARCHAR(20) NOT NULL DEFAULT 'MEDIUM'",
    "remarks": "remarks TEXT NULL",
    "procurement_remarks": "procurement_remarks TEXT NULL",
    "internal_notes": "internal_notes TEXT NULL",
}

PHASE2_FOLLOWUP_COLUMNS = {
    "legacy_buyer_id": "legacy_buyer_id VARCHAR(50) NULL",
    "buyer_name": "buyer_name VARCHAR(255) NULL",
    "country": "country VARCHAR(100) NULL",
    "assigned_to": "assigned_to VARCHAR(100) NULL",
    "transfer_to": "transfer_to VARCHAR(100) NULL",
    "mode": "mode VARCHAR(50) NULL",
    "status": "status VARCHAR(50) NULL",
}

PHASE3_LEAD_COLUMNS = {
    "sheet_source": "sheet_source VARCHAR(50) NULL",
    "first_contact_date": "first_contact_date DATE NULL",
}

PHASE4_LEAD_COLUMNS = {
    "lead_category": "lead_category VARCHAR(5) NULL",
    "buyer_engagement_frequency": "buyer_engagement_frequency VARCHAR(20) NULL",
    "next_action_plan": "next_action_plan TEXT NULL",
    "lost_reason": "lost_reason VARCHAR(100) NULL",
    "legacy_status": "legacy_status VARCHAR(50) NULL",
}

PHASE6_LEAD_COLUMNS = {
    "is_deleted": "is_deleted BOOLEAN NOT NULL DEFAULT 0",
    "created_at": "created_at DATETIME DEFAULT CURRENT_TIMESTAMP",
    "updated_at": "updated_at DATETIME DEFAULT CURRENT_TIMESTAMP",
    "deleted_at": "deleted_at DATETIME",
    "lead_score": "lead_score FLOAT NOT NULL DEFAULT 0",
    "address": "address TEXT",
    "inquiry_date": "inquiry_date DATE",
}

PHASE6_FOLLOWUP_COLUMNS = {
    "created_at": "created_at DATETIME DEFAULT CURRENT_TIMESTAMP",
}

PHASE6_ACTIVITYLOG_COLUMNS = {
    "user_name": "user_name VARCHAR(100)",
    "remarks": "remarks TEXT",
}

PHASE6_ORDER_COLUMNS = {
    "created_at": "created_at DATETIME DEFAULT CURRENT_TIMESTAMP",
    "updated_at": "updated_at DATETIME DEFAULT CURRENT_TIMESTAMP",
}

PHASE6_USER_COLUMNS = {
    "is_deleted": "is_deleted BOOLEAN NOT NULL DEFAULT 0",
    "phone": "phone VARCHAR(20)",
}


# ── Batched Phase 2 ───────────────────────────────────────────────────────────

def ensure_phase2_schema(engine: Engine) -> None:
    """Add Phase 2 columns + indexes."""
    if "leads" not in set(inspect(engine).get_table_names()):
        return
    _add_missing_columns(engine, "leads", PHASE2_LEAD_COLUMNS)
    if "followups" in set(inspect(engine).get_table_names()):
        _add_missing_columns(engine, "followups", PHASE2_FOLLOWUP_COLUMNS)

    if _is_mysql(engine):
        if _missing_index(engine, "leads", "ix_leads_priority"):
            with engine.begin() as c:
                c.execute(text("CREATE INDEX ix_leads_priority ON leads (priority_level)"))
        if _missing_index(engine, "leads", "ix_leads_legacy_buyer_id"):
            with engine.begin() as c:
                c.execute(text("CREATE INDEX ix_leads_legacy_buyer_id ON leads (legacy_buyer_id)"))


# ── Batched Phase 3 ───────────────────────────────────────────────────────────

def ensure_phase3_schema(engine: Engine) -> None:
    """Add Phase 3 columns."""
    _add_missing_columns(engine, "leads", PHASE3_LEAD_COLUMNS)


# ── Batched Phase 4 ───────────────────────────────────────────────────────────

def ensure_phase4_schema(engine: Engine) -> None:
    """Phase 4 — new 10-stage funnel."""
    if "leads" not in set(inspect(engine).get_table_names()):
        return
    _add_missing_columns(engine, "leads", PHASE4_LEAD_COLUMNS)

    if _is_mysql(engine):
        with engine.begin() as conn:
            conn.execute(text(
                "UPDATE leads SET legacy_status = status "
                "WHERE legacy_status IS NULL AND status IS NOT NULL"
            ))

        _STATUS_MAP = {
            "NEW": "Prospect", "Active": "Prospect", "OutReach": "Prospect",
            "Assigned": "Prospect", "Contacted": "Prospect", "New Lead": "Prospect",
            "Interested": "Requirement Qualified",
            "Requirement Understanding": "Requirement Qualified",
            "Meeting Scheduled": "Technical Discussion",
            "Meeting": "Technical Discussion",
            "Negotation": "Negotiation",
            "QUOTATION SENT": "Quotation Sent",
            "Samples Sent": "Sample Sent", "SAMPLE SENT": "Sample Sent",
            "Converted": "Order Closed", "CONVERTED": "Order Closed",
            "Nurture": "Nurturing", "NURTURING": "Nurturing",
            "Follow Up Stage": "Nurturing", "Follow Up": "Nurturing",
            "Inactive": "Nurturing", "INACTIVE": "Nurturing",
            "No Response": "Nurturing",
            "LOST": "Lost", "Not Interested": "Lost",
        }
        NEW_CANONICAL = {
            "Prospect", "Requirement Qualified", "Technical Discussion",
            "Quotation Sent", "Sample Sent", "Negotiation", "Trial Order",
            "Order Closed", "Nurturing", "Lost",
        }

        with engine.begin() as conn:
            when_clauses = " ".join(f"WHEN :o{i} THEN :n{i}" for i, o in enumerate(_STATUS_MAP))
            params = {}
            for i, (old, new) in enumerate(_STATUS_MAP.items()):
                params[f"o{i}"] = old
                params[f"n{i}"] = new
            params["default_status"] = "Prospect"
            conn.execute(
                text(
                    f"UPDATE leads SET status = CASE status {when_clauses} "
                    f"WHEN status NOT IN (:canonical) THEN :default_status ELSE status END"
                ).bindparams(bindparam("canonical", expanding=True)),
                params | {"canonical": list(NEW_CANONICAL)},
            )
            conn.execute(text("ALTER TABLE leads MODIFY COLUMN status VARCHAR(50) NOT NULL DEFAULT 'Prospect'"))


# ── Phase 5 data cleanup ───────────────────────────────────────────────────

def ensure_phase5_data_cleanup(engine: Engine) -> None:
    """Phase 5 — country/continent/source cleanup."""
    if "leads" not in set(inspect(engine).get_table_names()):
        return

    from modules.geo import normalize_country, country_continent, normalize_source

    with engine.begin() as conn:
        rows = conn.execute(text("SELECT DISTINCT country, lead_source FROM leads")).fetchall()
        country_map = {}
        source_map = {}
        for country, source in rows:
            if country:
                c = normalize_country(country)
                continent = country_continent(country)
                if (c, continent) != (country, None):
                    country_map[country] = (c, continent)
            if source:
                s = normalize_source(source)
                if s != source:
                    source_map[source] = s

        for old_country, (new_country, continent) in country_map.items():
            if continent:
                conn.execute(
                    text("UPDATE leads SET country = :c, continent = :cont WHERE country = :old"),
                    {"c": new_country, "cont": continent, "old": old_country},
                )
            else:
                conn.execute(
                    text("UPDATE leads SET country = :c WHERE country = :old"),
                    {"c": new_country, "old": old_country},
                )
        for old_source, new_source in source_map.items():
            conn.execute(
                text("UPDATE leads SET lead_source = :s WHERE lead_source = :old"),
                {"s": new_source, "old": old_source},
            )

    if "app_settings" in set(inspect(engine).get_table_names()):
        with engine.begin() as conn:
            done = conn.execute(
                text("SELECT setting_value FROM app_settings WHERE setting_key = 'category_reset_done'")
            ).fetchone()
            if not done:
                existing = _needed_columns(engine, "leads")
                if "lead_category" in existing:
                    conn.execute(text("UPDATE leads SET lead_category = NULL"))
                if _is_mysql(engine):
                    conn.execute(text(
                        "INSERT INTO app_settings (setting_key, setting_value) VALUES ('category_reset_done', 'yes') "
                        "ON DUPLICATE KEY UPDATE setting_value = 'yes'"
                    ))
                else:
                    conn.execute(text(
                        "INSERT OR REPLACE INTO app_settings (setting_key, setting_value) VALUES ('category_reset_done', 'yes')"
                    ))


# ── Assignment integrity ──────────────────────────────────────────────────────

def ensure_assignment_integrity(engine: Engine) -> int:
    """Guarantee NO lead has a blank/None owner."""
    if "leads" not in set(inspect(engine).get_table_names()):
        return 0
    with engine.begin() as conn:
        team = [r[0] for r in conn.execute(text(
            "SELECT DISTINCT assigned_to FROM leads "
            "WHERE assigned_to IS NOT NULL AND TRIM(assigned_to) <> '' AND deleted_at IS NULL"
        )).fetchall()]
        if not team:
            return 0
        loads = {
            t: conn.execute(text("SELECT COUNT(*) FROM leads WHERE assigned_to = :t AND deleted_at IS NULL"), {"t": t}).scalar()
            for t in team
        }
        orphans = [r[0] for r in conn.execute(text(
            "SELECT lead_id FROM leads WHERE (assigned_to IS NULL OR TRIM(assigned_to) = '') AND deleted_at IS NULL"
        )).fetchall()]
        now_func = "datetime('now')" if not _is_mysql(engine) else "NOW()"
        for lid in orphans:
            owner = min(loads, key=loads.get)
            conn.execute(text("UPDATE leads SET assigned_to = :o WHERE lead_id = :id"), {"o": owner, "id": lid})
            loads[owner] += 1
            if "activity_logs" in set(inspect(engine).get_table_names()):
                conn.execute(text(
                    f"INSERT INTO activity_logs (timestamp, action, user_name, lead_id, remarks) "
                    f"VALUES ({now_func}, 'AUTO_ASSIGN_ORPHAN', 'system', :id, :r)"
                ), {"id": lid, "r": f"Auto-assigned to {owner} — was blank in source sheet"})
        return len(orphans)


# ── Column defaults ───────────────────────────────────────────────────────────

def ensure_column_defaults(engine: Engine) -> None:
    """Patch NOT NULL columns — MySQL only (ORM handles defaults on SQLite)."""
    if not _is_mysql(engine):
        return
    if "leads" not in set(inspect(engine).get_table_names()):
        return
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE leads MODIFY COLUMN status VARCHAR(50) NOT NULL DEFAULT 'NEW'"))
        connection.execute(text("ALTER TABLE leads MODIFY COLUMN priority_level VARCHAR(20) NOT NULL DEFAULT 'MEDIUM'"))
        connection.execute(text("ALTER TABLE leads MODIFY COLUMN lead_score FLOAT NOT NULL DEFAULT 0"))
        indexes = {row[2] for row in connection.execute(text("SHOW INDEX FROM leads")).fetchall()}
        if "uq_leads_email" in indexes:
            connection.execute(text("ALTER TABLE leads DROP INDEX uq_leads_email"))


# ── Phase 6 ───────────────────────────────────────────────────────────────

def ensure_phase6_schema(engine: Engine) -> None:
    """Phase 6 — backfill is_deleted."""
    if "leads" in set(inspect(engine).get_table_names()):
        _add_missing_columns(engine, "leads", PHASE6_LEAD_COLUMNS)
        with engine.begin() as conn:
            conn.execute(text(
                "UPDATE leads SET is_deleted = 1 WHERE deleted_at IS NOT NULL AND is_deleted = 0"
            ))

    if "followups" in set(inspect(engine).get_table_names()):
        _add_missing_columns(engine, "followups", PHASE6_FOLLOWUP_COLUMNS)

    if "activity_logs" in set(inspect(engine).get_table_names()):
        _add_missing_columns(engine, "activity_logs", PHASE6_ACTIVITYLOG_COLUMNS)

    if "order_tracker" in set(inspect(engine).get_table_names()):
        _add_missing_columns(engine, "order_tracker", PHASE6_ORDER_COLUMNS)

    if "users" in set(inspect(engine).get_table_names()):
        _add_missing_columns(engine, "users", PHASE6_USER_COLUMNS)
        with engine.begin() as conn:
            conn.execute(text(
                "UPDATE users SET is_deleted = 1 WHERE deleted_at IS NOT NULL AND is_deleted = 0"
            ))

    if not _is_mysql(engine):
        return

    _FKS = [
        ("lead_transfers", "lead_id",
         "ALTER TABLE lead_transfers ADD CONSTRAINT fk_lead_transfers_lead "
         "FOREIGN KEY (lead_id) REFERENCES leads(lead_id) ON DELETE CASCADE"),
        ("deleted_leads", "lead_id",
         "ALTER TABLE deleted_leads ADD CONSTRAINT fk_deleted_leads_lead "
         "FOREIGN KEY (lead_id) REFERENCES leads(lead_id) ON DELETE SET NULL"),
    ]
    for table, column, ddl in _FKS:
        if table not in set(inspect(engine).get_table_names()):
            continue
        existing_fks = {fk["name"] for fk in inspect(engine).get_foreign_keys(table)}
        constraint_name = ddl.split("CONSTRAINT ")[1].split(" ")[0]
        if constraint_name in existing_fks:
            continue
        with engine.begin() as conn:
            try:
                conn.execute(text(ddl))
            except Exception:
                pass


# ── Phase 7 ───────────────────────────────────────────────────────────────

def ensure_phase7_schema(engine: Engine) -> None:
    """Phase 7 — recreate activity_logs with log_id PK if missing."""
    if "activity_logs" not in set(inspect(engine).get_table_names()):
        return
    existing = {col["name"] for col in inspect(engine).get_columns("activity_logs")}
    if "log_id" in existing:
        return
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE activity_logs"))
        if _is_mysql(engine):
            conn.execute(text(
                "CREATE TABLE activity_logs ("
                "  log_id INT AUTO_INCREMENT PRIMARY KEY,"
                "  timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,"
                "  action VARCHAR(100) NOT NULL,"
                "  user_name VARCHAR(100),"
                "  lead_id VARCHAR(32),"
                "  remarks TEXT,"
                "  INDEX ix_activity_logs_lead_timestamp (lead_id, timestamp),"
                "  INDEX ix_activity_logs_timestamp (timestamp),"
                "  INDEX ix_activity_logs_action (action)"
                ")"
            ))
        else:
            conn.execute(text(
                "CREATE TABLE activity_logs ("
                "  log_id INTEGER PRIMARY KEY AUTOINCREMENT,"
                "  timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,"
                "  action TEXT NOT NULL,"
                "  user_name TEXT,"
                "  lead_id TEXT,"
                "  remarks TEXT"
                ")"
            ))
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_activity_logs_lead_timestamp"
                " ON activity_logs (lead_id, timestamp)"
            ))
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_activity_logs_timestamp"
                " ON activity_logs (timestamp)"
            ))
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_activity_logs_action"
                " ON activity_logs (action)"
            ))


# ── Phase 8 — Sprint 2: Lead progression columns ──────────────────────────────

PHASE8_LEAD_COLUMNS = {
    "interest_level": "interest_level VARCHAR(20) NULL",
    "potential_deal_value": "potential_deal_value VARCHAR(50) NULL",
    "customer_requirements": "customer_requirements TEXT NULL",
}

PHASE9_LEAD_COLUMNS = {
    "has_pending_followup": "has_pending_followup BOOLEAN NOT NULL DEFAULT 0",
}


def ensure_phase9_schema(engine: Engine) -> None:
    """Add Sprint 3 — pipeline momentum indicator column."""
    if "leads" not in set(inspect(engine).get_table_names()):
        return
    _add_missing_columns(engine, "leads", PHASE9_LEAD_COLUMNS)


PHASE8_FOLLOWUP_COLUMNS = {
    "outcome_notes": "outcome_notes TEXT NULL",
    "completed_at": "completed_at DATETIME NULL",
    "completed_by": "completed_by VARCHAR(100) NULL",
}


def ensure_phase8_schema(engine: Engine) -> None:
    """Add Sprint 2 lead progression columns + followup completion columns."""
    if "leads" not in set(inspect(engine).get_table_names()):
        return
    _add_missing_columns(engine, "leads", PHASE8_LEAD_COLUMNS)
    if "followups" in set(inspect(engine).get_table_names()):
        _add_missing_columns(engine, "followups", PHASE8_FOLLOWUP_COLUMNS)


def ensure_phase10_schema(engine: Engine) -> None:
    """Create lead_handovers table for the Lead Transfer (Handover) system."""
    from sqlalchemy import text as sa_text
    existing = set(inspect(engine).get_table_names())
    if "lead_handovers" in existing:
        return
    with engine.connect() as conn:
        conn.execute(sa_text("""
            CREATE TABLE lead_handovers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id VARCHAR(32) NOT NULL,
                from_user VARCHAR(100) NOT NULL,
                to_user VARCHAR(100) NOT NULL,
                reason VARCHAR(50) NOT NULL,
                notes TEXT,
                status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
                requested_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                responded_at DATETIME,
                responded_by VARCHAR(100),
                created_by VARCHAR(100) NOT NULL
            )
        """))
        conn.execute(sa_text("CREATE INDEX ix_lead_handovers_lead_id ON lead_handovers (lead_id)"))
        conn.execute(sa_text("CREATE INDEX ix_lead_handovers_to_user ON lead_handovers (to_user)"))
        conn.execute(sa_text("CREATE INDEX ix_lead_handovers_status ON lead_handovers (status)"))
        conn.commit()


# ── Phase 11: Products ──────────────────────────────────────────────────────

PRODUCT_SEED_DATA = [
    # Spices
    ("Turmeric", "Spices"), ("Cumin", "Spices"), ("Black Pepper", "Spices"),
    ("Red Chili", "Spices"), ("Coriander", "Spices"), ("Mustard", "Spices"),
    # Pulses
    ("Moong Dal", "Pulses"), ("Toor Dal", "Pulses"), ("Chana Dal", "Pulses"), ("Urad Dal", "Pulses"),
    # Grains
    ("Basmati Rice", "Grains"), ("Wheat", "Grains"), ("Barley", "Grains"),
    # Herbs
    ("Moringa", "Herbs"), ("Ashwagandha", "Herbs"), ("Tulsi", "Herbs"),
    # Seeds
    ("Tomato Seeds", "Seeds"), ("Chili Seeds", "Seeds"), ("Cucumber Seeds", "Seeds"),
]


def ensure_phase11_schema(engine: Engine) -> None:
    """Create products and lead_products tables."""
    from sqlalchemy import text as sa_text
    existing = set(inspect(engine).get_table_names())

    if "products" not in existing:
        with engine.connect() as conn:
            conn.execute(sa_text("""
                CREATE TABLE products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(100) NOT NULL UNIQUE,
                    category VARCHAR(50) NOT NULL,
                    is_active BOOLEAN NOT NULL DEFAULT 1
                )
            """))
            for name, category in PRODUCT_SEED_DATA:
                conn.execute(sa_text(f"INSERT INTO products (name, category) VALUES ('{name}', '{category}')"))
            conn.commit()

    if "lead_products" not in existing:
        with engine.connect() as conn:
            conn.execute(sa_text("""
                CREATE TABLE lead_products (
                    lead_id VARCHAR(32) NOT NULL,
                    product_id INTEGER NOT NULL,
                    PRIMARY KEY (lead_id, product_id)
                )
            """))
            conn.execute(sa_text("CREATE INDEX ix_lead_products_lead_id ON lead_products (lead_id)"))
            conn.execute(sa_text("CREATE INDEX ix_lead_products_product_id ON lead_products (product_id)"))
            conn.commit()
