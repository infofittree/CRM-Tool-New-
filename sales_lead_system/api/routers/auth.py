"""Auth router — login, me."""

from __future__ import annotations

import time
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.auth import create_access_token
from api.deps import _get_db_connection, get_current_user, get_db
from api.schemas import ErrorResponse, LoginRequest, TokenResponse, UserResponse
from app.security import verify_password
from app.startup import ensure_default_admin
from database.models import User

router = APIRouter()

_login_attempts: dict[str, list[float]] = defaultdict(list)
_MAX_ATTEMPTS = 10
_LOCKOUT_SECONDS = 300


@router.post(
    "/login",
    response_model=TokenResponse,
    responses={401: {"model": ErrorResponse}},
)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    now = time.time()
    username_key = body.username.lower()
    attempts = _login_attempts[username_key]
    attempts[:] = [t for t in attempts if now - t < _LOCKOUT_SECONDS]
    if len(attempts) >= _MAX_ATTEMPTS:
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
        attempts.append(now)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    _login_attempts.pop(username_key, None)
    token = create_access_token({"sub": user.username})
    return TokenResponse(
        access_token=token,
        user=UserResponse(username=user.username, full_name=user.full_name, role=user.role, phone=user.phone),
    )


@router.get("/me", response_model=UserResponse)
def me(current_user: dict = Depends(get_current_user)):
    return UserResponse(**current_user)
