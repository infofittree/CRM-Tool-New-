"""Idempotent schema upgrades for local CRM deployments."""

from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


# Phase 3 — columns added to align with updated Google Sheet structure (2026-06-01)
# Tracks which sheet tab the lead originated from (Buyer_Master / Alibaba / other)
PHASE3_LEAD_COLUMN_DDL = {
    "sheet_source": "ALTER TABLE leads ADD COLUMN sheet_source VARCHAR(50) NULL COMMENT 'Google Sheet tab: Buyer_Master, Alibaba, etc.'",
    "first_contact_date": "ALTER TABLE leads ADD COLUMN first_contact_date DATE NULL COMMENT 'Maps to First Contact Date column in Google Sheet'",
}

LEAD_COLUMN_DDL = {
    "legacy_buyer_id": "ALTER TABLE leads ADD COLUMN legacy_buyer_id VARCHAR(50) NULL",
    "buyer_tag": "ALTER TABLE leads ADD COLUMN buyer_tag VARCHAR(20) NULL",
    "website": "ALTER TABLE leads ADD COLUMN website VARCHAR(255) NULL",
    "industry": "ALTER TABLE leads ADD COLUMN industry VARCHAR(120) NULL",
    "city": "ALTER TABLE leads ADD COLUMN city VARCHAR(120) NULL",
    "designation": "ALTER TABLE leads ADD COLUMN designation VARCHAR(120) NULL",
    "alternate_number": "ALTER TABLE leads ADD COLUMN alternate_number VARCHAR(50) NULL",
    "whatsapp_number": "ALTER TABLE leads ADD COLUMN whatsapp_number VARCHAR(50) NULL",
    "continent": "ALTER TABLE leads ADD COLUMN continent VARCHAR(100) NULL",
    "transfer_to": "ALTER TABLE leads ADD COLUMN transfer_to VARCHAR(100) NULL",
    "product_interest": "ALTER TABLE leads ADD COLUMN product_interest VARCHAR(255) NULL",
    "probability": "ALTER TABLE leads ADD COLUMN probability VARCHAR(20) NULL",
    "follow_up_stage": "ALTER TABLE leads ADD COLUMN follow_up_stage VARCHAR(50) NULL",
    "mode": "ALTER TABLE leads ADD COLUMN mode VARCHAR(50) NULL",
    "quotation_status": "ALTER TABLE leads ADD COLUMN quotation_status VARCHAR(50) NULL",
    "moq_requirement": "ALTER TABLE leads ADD COLUMN moq_requirement VARCHAR(100) NULL",
    "expected_quantity": "ALTER TABLE leads ADD COLUMN expected_quantity VARCHAR(100) NULL",
    "budget_range": "ALTER TABLE leads ADD COLUMN budget_range VARCHAR(100) NULL",
    "priority_level": "ALTER TABLE leads ADD COLUMN priority_level VARCHAR(20) NOT NULL DEFAULT 'MEDIUM'",
    "remarks": "ALTER TABLE leads ADD COLUMN remarks TEXT NULL",
    "procurement_remarks": "ALTER TABLE leads ADD COLUMN procurement_remarks TEXT NULL",
    "internal_notes": "ALTER TABLE leads ADD COLUMN internal_notes TEXT NULL",
}

FOLLOWUP_COLUMN_DDL = {
    "legacy_buyer_id": "ALTER TABLE followups ADD COLUMN legacy_buyer_id VARCHAR(50) NULL",
    "buyer_name": "ALTER TABLE followups ADD COLUMN buyer_name VARCHAR(255) NULL",
    "country": "ALTER TABLE followups ADD COLUMN country VARCHAR(100) NULL",
    "assigned_to": "ALTER TABLE followups ADD COLUMN assigned_to VARCHAR(100) NULL",
    "transfer_to": "ALTER TABLE followups ADD COLUMN transfer_to VARCHAR(100) NULL",
    "mode": "ALTER TABLE followups ADD COLUMN mode VARCHAR(50) NULL",
    "status": "ALTER TABLE followups ADD COLUMN status VARCHAR(50) NULL",
}


def ensure_phase2_schema(engine: Engine) -> None:
    """Add Phase 2 columns/indexes to an existing Phase 1 MySQL database."""
    inspector = inspect(engine)
    if "leads" not in set(inspector.get_table_names()):
        return

    existing_columns = {column["name"] for column in inspector.get_columns("leads")}
    with engine.begin() as connection:
        for column_name, ddl in LEAD_COLUMN_DDL.items():
            if column_name not in existing_columns:
                connection.execute(text(ddl))

    if "followups" in set(inspector.get_table_names()):
        existing_followup_columns = {column["name"] for column in inspector.get_columns("followups")}
        with engine.begin() as connection:
            for column_name, ddl in FOLLOWUP_COLUMN_DDL.items():
                if column_name not in existing_followup_columns:
                    connection.execute(text(ddl))

    inspector = inspect(engine)
    index_names = {index["name"] for index in inspector.get_indexes("leads")}
    if "ix_leads_priority" not in index_names:
        with engine.begin() as connection:
            connection.execute(text("CREATE INDEX ix_leads_priority ON leads (priority_level)"))
    if "ix_leads_legacy_buyer_id" not in index_names:
        with engine.begin() as connection:
            connection.execute(text("CREATE INDEX ix_leads_legacy_buyer_id ON leads (legacy_buyer_id)"))


def ensure_phase3_schema(engine: Engine) -> None:
    """Add Phase 3 columns to align with the updated Google Sheet structure (2026-06-01)."""
    inspector = inspect(engine)
    if "leads" not in set(inspector.get_table_names()):
        return
    existing_columns = {column["name"] for column in inspector.get_columns("leads")}
    with engine.begin() as connection:
        for column_name, ddl in PHASE3_LEAD_COLUMN_DDL.items():
            if column_name not in existing_columns:
                connection.execute(text(ddl))


def ensure_phase4_schema(engine: Engine) -> None:
    """Phase 4 — new 10-stage funnel (2026-06-02).

    Adds four new columns, saves legacy status, then migrates every lead's
    status to the new canonical value. Safe to re-run (idempotent).
    """
    if "leads" not in set(inspect(engine).get_table_names()):
        return

    existing = {col["name"] for col in inspect(engine).get_columns("leads")}

    with engine.begin() as conn:
        if "lead_category" not in existing:
            conn.execute(text("ALTER TABLE leads ADD COLUMN lead_category VARCHAR(5) NULL COMMENT 'A/B/C'"))
        if "buyer_engagement_frequency" not in existing:
            conn.execute(text("ALTER TABLE leads ADD COLUMN buyer_engagement_frequency VARCHAR(20) NULL COMMENT 'Frequent/Medium/Low'"))
        if "next_action_plan" not in existing:
            conn.execute(text("ALTER TABLE leads ADD COLUMN next_action_plan TEXT NULL"))
        if "lost_reason" not in existing:
            conn.execute(text("ALTER TABLE leads ADD COLUMN lost_reason VARCHAR(100) NULL"))
        if "legacy_status" not in existing:
            conn.execute(text("ALTER TABLE leads ADD COLUMN legacy_status VARCHAR(50) NULL COMMENT 'pre-migration status'"))

    # Save legacy status before touching it (only where not already saved)
    with engine.begin() as conn:
        conn.execute(text(
            "UPDATE leads SET legacy_status = status "
            "WHERE legacy_status IS NULL AND status IS NOT NULL"
        ))

    # Migrate status values to new canonical 10-stage funnel
    _STATUS_MAP = {
        "NEW": "Prospect",
        "Active": "Prospect",
        "OutReach": "Prospect",
        "Assigned": "Prospect",
        "Contacted": "Prospect",
        "New Lead": "Prospect",
        "Prospect": "Requirement Qualified",
        "Interested": "Requirement Qualified",
        "Requirement Understanding": "Requirement Qualified",
        "Meeting Scheduled": "Technical Discussion",
        "Meeting": "Technical Discussion",
        "Negotiation": "Negotiation",
        "Negotation": "Negotiation",
        "Quotation Sent": "Quotation Sent",
        "QUOTATION SENT": "Quotation Sent",
        "Samples Sent": "Sample Sent",
        "Sample Sent": "Sample Sent",
        "SAMPLE SENT": "Sample Sent",
        "Trial Order": "Trial Order",
        "Order Closed": "Order Closed",
        "Converted": "Order Closed",
        "CONVERTED": "Order Closed",
        "Nurture": "Nurturing",
        "NURTURING": "Nurturing",
        "Follow Up Stage": "Nurturing",
        "Follow Up": "Nurturing",
        "Inactive": "Nurturing",
        "INACTIVE": "Nurturing",
        "No Response": "Nurturing",
        "Lost": "Lost",
        "LOST": "Lost",
        "Not Interested": "Lost",
        # already canonical (pass-through)
        "Requirement Qualified": "Requirement Qualified",
        "Technical Discussion": "Technical Discussion",
        "Nurturing": "Nurturing",
    }
    NEW_CANONICAL = {
        "Prospect", "Requirement Qualified", "Technical Discussion",
        "Quotation Sent", "Sample Sent", "Negotiation", "Trial Order",
        "Order Closed", "Nurturing", "Lost",
    }
    with engine.begin() as conn:
        for old, new in _STATUS_MAP.items():
            if old not in NEW_CANONICAL:  # skip already-canonical values
                conn.execute(
                    text("UPDATE leads SET status = :new WHERE status = :old"),
                    {"new": new, "old": old},
                )
        # Catch any remaining unknown values → Prospect
        conn.execute(text(
            f"UPDATE leads SET status = 'Prospect' "
            f"WHERE status NOT IN ({','.join(':s' + str(i) for i in range(len(NEW_CANONICAL)))})"
        ), {f"s{i}": v for i, v in enumerate(NEW_CANONICAL)})

    # Update server default to match new canonical
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE leads MODIFY COLUMN status VARCHAR(50) NOT NULL DEFAULT 'Prospect'"))


def ensure_phase5_data_cleanup(engine: Engine) -> None:
    """Phase 5 patch (2026-06-03) — country cleanup, continent auto-fill,
    lead source normalisation, and A/B/C category reset.

    Idempotent and additive. Uses geo.py as the mapping source of truth.
    """
    if "leads" not in set(inspect(engine).get_table_names()):
        return

    from modules.geo import normalize_country, country_continent, normalize_source

    # Country/continent/source normalisation is idempotent — safe every startup.
    with engine.begin() as conn:
        rows = conn.execute(text("SELECT lead_id, country, lead_source FROM leads")).fetchall()
        for lead_id, country, source in rows:
            conn.execute(
                text("UPDATE leads SET country = :c, continent = :cont, lead_source = :s WHERE lead_id = :id"),
                {"c": normalize_country(country), "cont": country_continent(country),
                 "s": normalize_source(source), "id": lead_id},
            )

    # Patch 6: category reset runs ONCE ONLY — never wipe manually-set categories
    # on later restarts. Guarded by an app_settings flag.
    if "app_settings" in set(inspect(engine).get_table_names()):
        with engine.begin() as conn:
            done = conn.execute(
                text("SELECT setting_value FROM app_settings WHERE setting_key = 'category_reset_done'")
            ).fetchone()
            if not done:
                conn.execute(text("UPDATE leads SET lead_category = NULL"))
                conn.execute(text(
                    "INSERT INTO app_settings (setting_key, setting_value) VALUES ('category_reset_done', 'yes') "
                    "ON DUPLICATE KEY UPDATE setting_value = 'yes'"
                ))


def ensure_assignment_integrity(engine: Engine) -> int:
    """Patch (2026-06-03) — guarantee NO lead has a blank/None owner.

    The source Google Sheet contains blank 'Assigned to' rows. Since there is no
    original owner to recover, ownerless leads are distributed to the least-loaded
    active salesperson (fair balancing) and the action is logged to activity_logs
    for full transparency. Idempotent — a no-op once all leads have owners.

    Returns the number of leads repaired.
    """
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
        for lid in orphans:
            owner = min(loads, key=loads.get)  # least-loaded salesperson
            conn.execute(text("UPDATE leads SET assigned_to = :o WHERE lead_id = :id"), {"o": owner, "id": lid})
            loads[owner] += 1
            if "activity_logs" in set(inspect(engine).get_table_names()):
                conn.execute(text(
                    "INSERT INTO activity_logs (timestamp, action, user_name, lead_id, remarks) "
                    "VALUES (NOW(), 'AUTO_ASSIGN_ORPHAN', 'system', :id, :r)"
                ), {"id": lid, "r": f"Auto-assigned to {owner} — was blank in source sheet"})
        return len(orphans)


def ensure_column_defaults(engine: Engine) -> None:
    """Patch NOT NULL columns and remove overly strict unique constraints.

    Safe to re-run — each statement is guarded before execution.
    """
    if "leads" not in set(inspect(engine).get_table_names()):
        return

    with engine.begin() as connection:
        # Add server-side defaults so MySQL never sees NULL for NOT NULL columns
        connection.execute(text("ALTER TABLE leads MODIFY COLUMN status VARCHAR(50) NOT NULL DEFAULT 'NEW'"))
        connection.execute(text("ALTER TABLE leads MODIFY COLUMN priority_level VARCHAR(20) NOT NULL DEFAULT 'MEDIUM'"))
        connection.execute(text("ALTER TABLE leads MODIFY COLUMN lead_score FLOAT NOT NULL DEFAULT 0"))

        # Drop the email unique constraint — CRM allows multiple records per email
        indexes = {row[2] for row in connection.execute(text("SHOW INDEX FROM leads")).fetchall()}
        if "uq_leads_email" in indexes:
            connection.execute(text("ALTER TABLE leads DROP INDEX uq_leads_email"))
