"""SQLAlchemy database connection management — MySQL + SQLite local dev."""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from config.settings import MySQLSettings, get_mysql_settings


class DatabaseConnection:
    """Create pooled SQLAlchemy engines and sessions."""

    def __init__(self, settings: MySQLSettings | None = None, logger: logging.Logger | None = None) -> None:
        self.settings = settings or get_mysql_settings()
        self.logger = logger or logging.getLogger(__name__)
        self.last_error_message: str | None = None
        self.engine = self._create_engine()
        self.session_factory = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, expire_on_commit=False)
        # Enable WAL mode + foreign keys for SQLite
        if self.settings.is_sqlite:
            self._setup_sqlite()

    def _setup_sqlite(self) -> None:
        with self.engine.connect() as conn:
            conn.execute(text("PRAGMA journal_mode=WAL"))
            conn.execute(text("PRAGMA foreign_keys=ON"))
            conn.commit()

    def _create_engine(self) -> Engine:
        url = self.settings.sqlalchemy_url
        if self.settings.is_sqlite:
            return create_engine(url, echo=False, future=True)
        # PostgreSQL or MySQL
        connect_args = {}
        if "postgresql" in url:
            connect_args["sslmode"] = "require"
        return create_engine(
            url,
            pool_pre_ping=True,
            pool_recycle=self.settings.pool_recycle_seconds,
            pool_size=self.settings.pool_size,
            max_overflow=self.settings.max_overflow,
            pool_timeout=self.settings.pool_timeout_seconds,
            connect_args=connect_args,
            echo=False,
            future=True,
        )

    def create_server_engine(self) -> Engine:
        """Create a temporary engine that connects without selecting a database (MySQL only)."""
        if self.settings.is_sqlite:
            return self.engine
        return create_engine(
            self.settings.server_sqlalchemy_url,
            pool_pre_ping=True,
            pool_recycle=self.settings.pool_recycle_seconds,
            pool_timeout=self.settings.pool_timeout_seconds,
            echo=False,
            future=True,
        )

    def ensure_database_exists(self) -> None:
        """Create the configured database if credentials allow it (MySQL only)."""
        if self.settings.is_sqlite:
            return
        server_engine = self.create_server_engine()
        try:
            database_name = self.settings.database.replace("`", "``")
            with server_engine.begin() as connection:
                connection.execute(text(f"CREATE DATABASE IF NOT EXISTS `{database_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
        finally:
            server_engine.dispose()

    _CONTROL_FLOW_EXC = {"RerunException", "RerunData", "StopException", "StreamlitAPIException"}

    @contextmanager
    def session_scope(self) -> Iterator[Session]:
        """Provide a transactional session with commit/rollback handling."""
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except SQLAlchemyError:
            session.rollback()
            self.logger.exception("Database operation failed")
            raise
        except BaseException as exc:
            if type(exc).__name__ in self._CONTROL_FLOW_EXC:
                try:
                    session.commit()
                except SQLAlchemyError:
                    session.rollback()
                    self.logger.exception("Commit on rerun failed")
            else:
                session.rollback()
                self.logger.exception("Unexpected database operation failure")
            raise
        finally:
            session.close()

    def health_check(self) -> bool:
        """Verify that the database is reachable."""
        self.last_error_message = None
        try:
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return True
        except SQLAlchemyError as exc:
            self.last_error_message = self.format_connection_error(exc)
            self.logger.error("Database health check failed: %s", self.last_error_message)
            return False

    def dispose(self) -> None:
        """Close all pooled connections."""
        self.engine.dispose()

    def format_connection_error(self, exc: SQLAlchemyError) -> str:
        """Create a concise, password-safe error message."""
        if self.settings.is_sqlite:
            return f"SQLite error: {exc}"
        original = getattr(exc, "orig", exc)
        error_code = getattr(original, "errno", None)
        message = str(original)

        if error_code == 1045 or "1045" in message:
            if self.settings.password == "change_me":
                return (
                    f"MySQL rejected the configured login ({self.settings.redacted_dsn}). "
                    "MYSQL_PASSWORD is still set to the placeholder 'change_me' in config/.env."
                )
            return (
                f"MySQL rejected the configured login ({self.settings.redacted_dsn}). "
                "Update MYSQL_USER and MYSQL_PASSWORD in config/.env, then run "
                "`python main.py healthcheck-mysql` again."
            )

        if error_code == 1049 or "Unknown database" in message:
            return (
                f"MySQL database '{self.settings.database}' does not exist. "
                "Create it with `mysql -u root -p < database/schema.sql` or update MYSQL_DATABASE in config/.env."
            )

        return f"MySQL connection failed for {self.settings.redacted_dsn}: {message}"
