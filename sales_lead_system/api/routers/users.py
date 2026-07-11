"""Users router — management endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.deps import get_current_user, get_db, require_role
from api.schemas import UserCreate, UserResponse, UserWorkload
from database.models import User
from modules.crm_service import CRMService

router = APIRouter()


@router.get("", response_model=list[UserResponse])
def list_users(
    current_user: dict = Depends(require_role(["Admin", "Manager"])),
    db: Session = Depends(get_db),
):
    users = db.scalars(select(User).where(User.is_active.is_(True)).order_by(User.full_name)).all()
    return [UserResponse(username=u.username, full_name=u.full_name, role=u.role, phone=u.phone) for u in users]


@router.get("/transfer-recipients", response_model=list[UserResponse])
def transfer_recipients(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return all active users eligible to receive a lead transfer."""
    users = db.scalars(select(User).where(User.is_active.is_(True)).order_by(User.full_name)).all()
    return [UserResponse(username=u.username, full_name=u.full_name, role=u.role, phone=u.phone) for u in users]


@router.get("/salespersons", response_model=list[str])
def salespersons(
    current_user: dict = Depends(require_role(["Admin", "Manager"])),
    db: Session = Depends(get_db),
):
    service = CRMService(db)
    return service.get_salespersons()


@router.get("/workload/{full_name}", response_model=UserWorkload)
def workload(
    full_name: str,
    current_user: dict = Depends(require_role(["Admin", "Manager"])),
    db: Session = Depends(get_db),
):
    service = CRMService(db)
    return UserWorkload(**service.user_workload(full_name))


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    body: UserCreate,
    current_user: dict = Depends(require_role(["Admin"])),
    db: Session = Depends(get_db),
):
    existing = db.scalar(select(User).where(User.username == body.username))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")
    service = CRMService(db)
    service.create_user(body.username, body.password, body.full_name, body.role, phone=body.phone)
    return UserResponse(username=body.username, full_name=body.full_name, role=body.role, phone=body.phone)


@router.delete("/{username}")
def delete_user(
    username: str,
    mode: str = Query("transfer"),
    transfer_to: str | None = Query(None),
    current_user: dict = Depends(require_role(["Admin"])),
    db: Session = Depends(get_db),
):
    service = CRMService(db)
    ok, message = service.delete_user(username, current_user, mode=mode, transfer_to=transfer_to)
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    return {"message": message}
