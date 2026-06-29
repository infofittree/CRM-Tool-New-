"""FastAPI dependency injection — DB sessions, auth, role guards."""

from __future__ import annotations

import logging
from typing import Any, Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.auth import decode_token
from database.db_connection import DatabaseConnection
from database.models import User

security = HTTPBearer(auto_error=False)

_db: DatabaseConnection | None = None


def _get_db_connection() -> DatabaseConnection:
    global _db
    if _db is None:
        _db = DatabaseConnection(logger=logging.getLogger("api"))
    return _db


def get_db() -> Generator[Session, None, None]:
    db = _get_db_connection()
    with db.session_scope() as session:
        yield session


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    payload = decode_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
    user = db.scalar(select(User).where(User.username == username, User.is_active.is_(True)))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    return {"username": user.username, "full_name": user.full_name, "role": user.role}


def require_role(required_roles: list[str]):
    def checker(user: dict = Depends(get_current_user)) -> dict:
        if user["role"] not in required_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user
    return checker
