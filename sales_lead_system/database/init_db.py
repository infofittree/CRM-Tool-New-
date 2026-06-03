"""Database initialization script for SQLAlchemy-managed tables."""

from __future__ import annotations

from database.db_connection import DatabaseConnection
from database.models import Base
from database.schema_manager import ensure_phase2_schema
from modules.logger import setup_logger
from config.settings import LOG_DIR


def init_database() -> None:
    """Create all ORM tables in the configured MySQL database."""
    logger = setup_logger(LOG_DIR)
    connection = DatabaseConnection(logger=logger)
    connection.ensure_database_exists()
    Base.metadata.create_all(connection.engine)
    ensure_phase2_schema(connection.engine)
    logger.info("MySQL tables initialized")
    print("MySQL tables initialized successfully.")


if __name__ == "__main__":
    init_database()
