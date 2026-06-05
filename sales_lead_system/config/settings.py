"""Environment-driven application settings."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / "config" / ".env")


@dataclass(frozen=True)
class MySQLSettings:
    """MySQL connection and pool settings."""

    host: str
    port: int
    user: str
    password: str
    database: str
    pool_size: int = 10
    max_overflow: int = 20
    pool_recycle_seconds: int = 1800
    pool_timeout_seconds: int = 30
    ssl: bool = False  # most hosted MySQL (Aiven, Railway, etc.) require SSL

    @property
    def _query(self) -> str:
        q = "charset=utf8mb4"
        if self.ssl:
            # mysql-connector enables TLS without a local CA when ssl_disabled=false
            q += "&ssl_disabled=false"
        return q

    @property
    def sqlalchemy_url(self) -> str:
        """Return a SQLAlchemy URL for mysql-connector-python."""
        user = quote_plus(self.user)
        password = quote_plus(self.password)
        host = quote_plus(self.host)
        database = quote_plus(self.database)
        return (
            f"mysql+mysqlconnector://{user}:{password}"
            f"@{host}:{self.port}/{database}?{self._query}"
        )

    @property
    def server_sqlalchemy_url(self) -> str:
        """Return a server-level SQLAlchemy URL without a database name."""
        user = quote_plus(self.user)
        password = quote_plus(self.password)
        host = quote_plus(self.host)
        return f"mysql+mysqlconnector://{user}:{password}@{host}:{self.port}/?{self._query}"

    @property
    def redacted_dsn(self) -> str:
        """Return a safe connection label for logs and CLI output."""
        return f"{self.user}@{self.host}:{self.port}/{self.database}"


def _read_streamlit_secrets() -> dict:
    """Return the [mysql] section from Streamlit secrets, or {} if unavailable.

    On Streamlit Cloud, DB credentials live in the app's Secrets (secrets.toml)
    under a [mysql] table. Locally (CLI / no secrets file) this safely returns {}
    and the loader falls back to environment variables / .env.
    """
    try:
        import streamlit as st  # available in the app runtime
        if "mysql" in st.secrets:
            return dict(st.secrets["mysql"])
    except Exception:
        pass
    return {}


def get_mysql_settings() -> MySQLSettings:
    """Load MySQL settings — Streamlit secrets first, then environment/.env."""
    import os

    sec = _read_streamlit_secrets()

    def val(key: str, default: str) -> str:
        # priority: Streamlit secrets [mysql] -> env var -> default
        # secrets use short keys (host, port, ...) i.e. MYSQL_ prefix stripped.
        # .strip() guards against trailing spaces/newlines pasted into secrets.
        short = key.removeprefix("MYSQL_").lower()
        if short in sec and sec[short] not in (None, ""):
            return str(sec[short]).strip()
        env_val = os.getenv(key)
        if env_val is not None and env_val != "":
            return env_val.strip()
        return default

    return MySQLSettings(
        host=val("MYSQL_HOST", "localhost"),
        port=int(val("MYSQL_PORT", "3306")),
        user=val("MYSQL_USER", "root"),
        password=val("MYSQL_PASSWORD", ""),
        database=val("MYSQL_DATABASE", "sales_lead_crm"),
        pool_size=int(val("MYSQL_POOL_SIZE", "10")),
        max_overflow=int(val("MYSQL_MAX_OVERFLOW", "20")),
        pool_recycle_seconds=int(val("MYSQL_POOL_RECYCLE_SECONDS", "1800")),
        pool_timeout_seconds=int(val("MYSQL_POOL_TIMEOUT_SECONDS", "30")),
        ssl=str(val("MYSQL_SSL", "false")).strip().lower() in ("1", "true", "yes", "on"),
    )


EXPORT_DIR = PROJECT_ROOT / "exports"
LOG_DIR = PROJECT_ROOT / "logs"
CONFIG_DIR = PROJECT_ROOT / "config"
BACKUP_DIR = PROJECT_ROOT / "data" / "backup"
