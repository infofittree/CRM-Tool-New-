"""Check all ORM tables for column mismatches with actual database schema."""
from __future__ import annotations

from sqlalchemy import inspect

from database.db_connection import DatabaseConnection
from database.models import Base

db = DatabaseConnection()
insp = inspect(db.engine)

for table_name in sorted(insp.get_table_names()):
    actual = {c["name"] for c in insp.get_columns(table_name)}
    orm_class = None
    for mapper in Base.registry.mappers:
        if mapper.tables[0].name == table_name:
            orm_class = mapper.class_
            break
    if orm_class is None:
        print(f"{table_name}: NO ORM CLASS (data-only table)")
        continue
    orm_cols = {c.name for c in orm_class.__table__.columns}
    missing = orm_cols - actual
    extra = actual - orm_cols
    if missing or extra:
        parts = []
        if missing:
            parts.append(f"ORM missing: {sorted(missing)}")
        if extra:
            parts.append(f"Extra in table: {sorted(extra)}")
        print(f"{table_name}: {' | '.join(parts)}")
    else:
        print(f"{table_name}: OK")
