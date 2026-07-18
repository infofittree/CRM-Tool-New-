"""Auth router — login, me."""

from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from api.auth import create_access_token
from api.deps import _get_db_connection, get_current_user, get_db
from api.schemas import ErrorResponse, LoginRequest, TokenResponse, UserResponse
from app.security import verify_password
from app.startup import ensure_default_admin
from database.models import LoginAttempt, User

router = APIRouter()

_MAX_ATTEMPTS = 10
_LOCKOUT_SECONDS = 300


def _record_failed_attempt(db_conn, username_key: str, now: datetime) -> None:
    """Append a single failed-login row and prune entries older than the window."""
    db_conn.add(LoginAttempt(username_key=username_key, attempted_at=now))
    db_conn.execute(
        delete(LoginAttempt).where(
            LoginAttempt.username_key == username_key,
            LoginAttempt.attempted_at < now - timedelta(seconds=_LOCKOUT_SECONDS),
        )
    )


def _prune_attempts(db_conn, username_key: str, now: datetime) -> None:
    """Best-effort prune without inserting a new attempt (used on success)."""
    db_conn.execute(
        delete(LoginAttempt).where(
            LoginAttempt.username_key == username_key,
            LoginAttempt.attempted_at < now - timedelta(seconds=_LOCKOUT_SECONDS),
        )
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    responses={401: {"model": ErrorResponse}},
)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    now = datetime.utcnow()
    username_key = body.username.lower()

    # Count recent failures for this username from the persistent ledger.
    recent_failures = db.scalar(
        select(func.count()).select_from(LoginAttempt).where(
            LoginAttempt.username_key == username_key,
            LoginAttempt.attempted_at >= now - timedelta(seconds=_LOCKOUT_SECONDS),
        )
    ) or 0
    if recent_failures >= _MAX_ATTEMPTS:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many login attempts. Try again later.")

    ensure_default_admin(_get_db_connection())
    user = db.scalar(
        select(User).where(
            User.username == body.username,
            User.is_active.is_(True),
            User.deleted_at.is_(None),
        )
    )
    if not user or not verify_password(body.password, user.password_hash):
        _record_failed_attempt(db, username_key, now)
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    # Successful login — drop any prior attempts so the user starts fresh.
    _prune_attempts(db, username_key, now)
    db.commit()
    token = create_access_token({"sub": user.username})
    return TokenResponse(
        access_token=token,
        user=UserResponse(username=user.username, full_name=user.full_name, role=user.role, phone=user.phone),
    )


@router.get("/me", response_model=UserResponse)
def me(current_user: dict = Depends(get_current_user)):
    return UserResponse(**current_user)
