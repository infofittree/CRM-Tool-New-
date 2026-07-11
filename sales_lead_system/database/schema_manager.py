def ensure_phase11_schema(engine: Engine) -> None:
    """Create products and lead_products tables."""
    from sqlalchemy import text as sa_text
    existing = set(inspect(engine).get_table_names())
    is_pg = _is_postgres(engine)

    if "products" not in existing:
        with engine.connect() as conn:
            if is_pg:
                conn.execute(sa_text("""
                    CREATE TABLE products (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(100) NOT NULL UNIQUE,
                        category VARCHAR(50) NOT NULL,
                        is_active BOOLEAN NOT NULL DEFAULT TRUE
                    )
                """))
            else:
                conn.execute(sa_text("""
                    CREATE TABLE products (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name VARCHAR(100) NOT NULL UNIQUE,
                        category VARCHAR(50) NOT NULL,
                        is_active BOOLEAN NOT NULL DEFAULT 1
                    )
                """))
            for name, category in PRODUCT_SEED_DATA:
                conn.execute(sa_text("INSERT INTO products (name, category) VALUES (:name, :category)"), {"name": name, "category": category})
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


# ── Phase 12: Inquiry Revisions ─────────────────────────────────────────────

def ensure_phase12_schema(engine: Engine) -> None:
    """Create inquiry_revisions table for negotiation tracking."""
    from sqlalchemy import text as sa_text
    existing = set(inspect(engine).get_table_names())
    if "inquiry_revisions" in existing:
        return
    is_pg = _is_postgres(engine)
    with engine.connect() as conn:
        if is_pg:
            conn.execute(sa_text("""
                CREATE TABLE inquiry_revisions (
                    id SERIAL PRIMARY KEY,
                    inquiry_id INTEGER NOT NULL,
                    revision_number INTEGER NOT NULL,
                    created_by VARCHAR(100) NOT NULL,
                    reason VARCHAR(50) NOT NULL,
                    customer_feedback TEXT,
                    target_price VARCHAR(50),
                    quantity VARCHAR(50),
                    packaging VARCHAR(50),
                    delivery_timeline VARCHAR(50),
                    payment_terms VARCHAR(50),
                    additional_requirements TEXT,
                    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    responded_at TIMESTAMP,
                    responded_by VARCHAR(100)
                )
            """)
        else:
            conn.execute(sa_text("""
                CREATE TABLE inquiry_revisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    inquiry_id INTEGER NOT NULL,
                    revision_number INTEGER NOT NULL,
                    created_by VARCHAR(100) NOT NULL,
                    reason VARCHAR(50) NOT NULL,
                    customer_feedback TEXT,
                    target_price VARCHAR(50),
                    quantity VARCHAR(50),
                    packaging VARCHAR(50),
                    delivery_timeline VARCHAR(50),
                    payment_terms VARCHAR(50),
                    additional_requirements TEXT,
                    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    responded_at DATETIME,
                    responded_by VARCHAR(100)
                )
            """)
        conn.execute(sa_text("CREATE INDEX ix_inquiry_revisions_inquiry_id ON inquiry_revisions (inquiry_id)"))
        conn.commit()
