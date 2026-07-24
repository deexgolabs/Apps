from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_admin_user
from app.models import User, App
from app.schemas import AdminUserResponse, AdminUserUpdate, AdminAppResponse

router = APIRouter(prefix="/api/admin", tags=["admin"])

_VALID_PLANS = {"free", "pro", "business"}


@router.get("/users", response_model=list[AdminUserResponse])
async def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    rows = (
        db.query(User, func.count(App.id).label("app_count"))
        .outerjoin(App, App.user_id == User.id)
        .group_by(User.id)
        .order_by(User.created_at.desc())
        .all()
    )
    return [
        AdminUserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            plan=user.plan,
            is_active=user.is_active,
            is_admin=user.is_admin,
            is_verified=user.is_verified,
            created_at=user.created_at,
            app_count=app_count,
        )
        for user, app_count in rows
    ]


@router.put("/users/{user_id}", response_model=AdminUserResponse)
async def update_user(
    user_id: int,
    payload: AdminUserUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if payload.plan is not None:
        if payload.plan not in _VALID_PLANS:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid plan")
        user.plan = payload.plan
    if payload.is_admin is not None:
        user.is_admin = payload.is_admin
    if payload.is_active is not None:
        user.is_active = payload.is_active

    db.commit()
    db.refresh(user)

    app_count = db.query(func.count(App.id)).filter(App.user_id == user.id).scalar()
    return AdminUserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        plan=user.plan,
        is_active=user.is_active,
        is_admin=user.is_admin,
        is_verified=user.is_verified,
        created_at=user.created_at,
        app_count=app_count,
    )


@router.get("/apps", response_model=list[AdminAppResponse])
async def list_apps(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    rows = (
        db.query(App, User.email)
        .join(User, App.user_id == User.id)
        .order_by(App.created_at.desc())
        .all()
    )
    return [
        AdminAppResponse(
            id=app.id,
            name=app.name,
            status=app.status,
            template_type=app.template_type,
            owner_email=owner_email,
            created_at=app.created_at,
        )
        for app, owner_email in rows
    ]
