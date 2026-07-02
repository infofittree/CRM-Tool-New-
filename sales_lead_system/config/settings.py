"""Environment-driven application settings — MySQL + SQLite local dev."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / "config" / ".env")


def _env(key: str, default: str = "") -> str:
    val = os.getenv(key)
    return val.strip() if val else default


def _env_bool(key: str, default: bool = False) -> bool:
    val = os.getenv(key, "").strip().lower()
    if val:
        return val in ("1", "true", "yes", "on")
    return default


@dataclass(frozen=True)
class MySQLSettings:
    """Connection settings — MySQL (production) or SQLite (local dev)."""

    # SQLite mode
    use_sqlite: bool = False
    sqlite_db_path: str = ""

    # MySQL
    host: str = "localhost"
    port: int = 3306
    user: str = "root"
    password: str = ""
    database: str = "sales_lead_crm"
    pool_size: int = 10
    max_overflow: int = 20
    pool_recycle_seconds: int = 1800
    pool_timeout_seconds: int = 30
    ssl: bool = False

    @property
    def is_sqlite(self) -> bool:
        return self.use_sqlite

    @property
    def sqlalchemy_url(self) -> str:
        if self.use_sqlite:
            db_path = Path(self.sqlite_db_path)
            if not db_path.is_absolute():
                db_path = PROJECT_ROOT / db_path
            db_path.parent.mkdir(parents=True, exist_ok=True)
            return f"sqlite:///{db_path.as_posix()}"
        user = quote_plus(self.user)
        password = quote_plus(self.password)
        host = quote_plus(self.host)
        database = quote_plus(self.database)
        q = "charset=utf8mb4"
        if self.ssl:
            q += "&ssl_disabled=false"
        return f"mysql+mysqlconnector://{user}:{password}@{host}:{self.port}/{database}?{q}"

    @property
    def server_sqlalchemy_url(self) -> str:
        if self.use_sqlite:
            return self.sqlalchemy_url
        user = quote_plus(self.user)
        password = quote_plus(self.password)
        host = quote_plus(self.host)
        return f"mysql+mysqlconnector://{user}:{password}@{host}:{self.port}/?charset=utf8mb4"

    @property
    def redacted_dsn(self) -> str:
        if self.use_sqlite:
            return f"sqlite:///{self.sqlite_db_path}"
        return f"{self.user}@{self.host}:{self.port}/{self.database}"


def _read_streamlit_secrets() -> dict:
    try:
        import sys
        if "streamlit" in sys.modules:
            import streamlit as st
            if "mysql" in st.secrets:
                return dict(st.secrets["mysql"])
    except Exception:
        pass
    return {}


def get_mysql_settings() -> MySQLSettings:
    """Load settings — Streamlit secrets first, then environment/.env."""
    sec = _read_streamlit_secrets()

    def val(key: str, default: str) -> str:
        short = key.removeprefix("MYSQL_").lower()
        if short in sec and sec[short] not in (None, ""):
            return str(sec[short]).strip()
        env_val = os.getenv(key)
        if env_val is not None and env_val != "":
            return env_val.strip()
        return default

    use_sqlite = _env_bool("USE_SQLITE", False)
    sqlite_path = _env("SQLITE_DB_PATH", "database/crm_local.db")

    if use_sqlite:
        return MySQLSettings(
            use_sqlite=True,
            sqlite_db_path=sqlite_path,
            database="",  # not used for SQLite
        )

    return MySQLSettings(
        use_sqlite=False,
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
