"""Default-user seeding used by the FastAPI auth flow.

Kept separate from any Streamlit-era startup code. The single exposed
function, :func:`ensure_default_admin`, is called on every login attempt
in ``api/routers/auth.py`` and is idempotent — it only inserts seed users
when the ``users`` table is completely empty.
"""

from __future__ import annotations

import json
import logging
import os

from sqlalchemy import select

from app.security import hash_password
from database.db_connection import DatabaseConnection
from database.models import User


def ensure_default_admin(db: DatabaseConnection) -> None:
    """Seed default users from the ``DEFAULT_USERS_JSON`` env var.

    Format: a JSON array of ``[username, password, full_name, role]`` tuples.
    Safely no-ops when the users table already contains rows or when the
    env var is absent / malformed — the API has a working login regardless
    of whether seeding runs.
    """

    logger = logging.getLogger("api")

    with db.session_scope() as session:
        has_user = session.scalar(select(User.user_id).limit(1))
        if has_user:
            return

        users_json = os.getenv("DEFAULT_USERS_JSON", "")
        if not users_json:
            logger.warning("DEFAULT_USERS_JSON not set — no default users created")
            return
        try:
            users_data = json.loads(users_json)
        except (json.JSONDecodeError, TypeError):
            logger.error("DEFAULT_USERS_JSON contains invalid JSON — no default users created")
            return

        for username, password, full_name, role in users_data:
            session.add(
                User(
                    username=username,
                    password_hash=hash_password(password),
                    full_name=full_name,
                    role=role,
                    is_active=True,
                )
            )
        session.commit()
