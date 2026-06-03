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

    @property
    def sqlalchemy_url(self) -> str:
        """Return a SQLAlchemy URL for mysql-connector-python."""
        user = quote_plus(self.user)
        password = quote_plus(self.password)
        host = quote_plus(self.host)
        database = quote_plus(self.database)
        return (
            f"mysql+mysqlconnector://{user}:{password}"
            f"@{host}:{self.port}/{database}?charset=utf8mb4"
        )

    @property
    def server_sqlalchemy_url(self) -> str:
        """Return a server-level SQLAlchemy URL without a database name."""
        user = quote_plus(self.user)
        password = quote_plus(self.password)
        host = quote_plus(self.host)
        return f"mysql+mysqlconnector://{user}:{password}@{host}:{self.port}/?charset=utf8mb4"

    @property
    def redacted_dsn(self) -> str:
        """Return a safe connection label for logs and CLI output."""
        return f"{self.user}@{self.host}:{self.port}/{self.database}"


def get_mysql_settings() -> MySQLSettings:
    """Load MySQL settings from environment variables."""
    import os

    return MySQLSettings(
        host=os.getenv("MYSQL_HOST", "localhost"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        database=os.getenv("MYSQL_DATABASE", "sales_lead_crm"),
        pool_size=int(os.getenv("MYSQL_POOL_SIZE", "10")),
        max_overflow=int(os.getenv("MYSQL_MAX_OVERFLOW", "20")),
        pool_recycle_seconds=int(os.getenv("MYSQL_POOL_RECYCLE_SECONDS", "1800")),
        pool_timeout_seconds=int(os.getenv("MYSQL_POOL_TIMEOUT_SECONDS", "30")),
    )


EXPORT_DIR = PROJECT_ROOT / "exports"
LOG_DIR = PROJECT_ROOT / "logs"
CONFIG_DIR = PROJECT_ROOT / "config"
BACKUP_DIR = PROJECT_ROOT / "data" / "backup"
