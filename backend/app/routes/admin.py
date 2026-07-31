from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.dependencies import get_current_admin_user
from app.models import (
    AdminAuditLog,
    App,
    PlanConfig,
    User,
)
from app.utils import delete_app_cascade
from app.schemas import (
    AdminAppDetailResponse,
    AdminAppResponse,
    AdminAppStatusUpdate,
    AdminAuditLogResponse,
    AdminStatsResponse,
    AdminUserResponse,
    AdminUserUpdate,
    PlanConfigResponse,
    PlanConfigUpdate,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])

_VALID_PLANS = {"free", "pro", "business"}
_VALID_APP_STATUSES = {"draft", "published", "suspended"}


def _log_audit(db: Session, admin: User, action: str, target: str, details: Optional[str] = None) -> None:
    db.add(AdminAuditLog(admin_id=admin.id, action=action, target=target, details=details))
    db.commit()


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
    admin: User = Depends(get_current_admin_user),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    changes = []
    if payload.plan is not None:
        if payload.plan not in _VALID_PLANS:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid plan")
        if payload.plan != user.plan:
            changes.append(f"plan: {user.plan} -> {payload.plan}")
        user.plan = payload.plan
        # concessão manual do admin não expira sozinha (evita reverter pra
        # free por causa de um plan_expires_at antigo de uma assinatura paga anterior)
        user.plan_expires_at = None
    if payload.is_admin is not None:
        if payload.is_admin != user.is_admin:
            changes.append(f"is_admin: {user.is_admin} -> {payload.is_admin}")
        user.is_admin = payload.is_admin
    if payload.is_active is not None:
        if payload.is_active != user.is_active:
            changes.append(f"is_active: {user.is_active} -> {payload.is_active}")
        user.is_active = payload.is_active

    db.commit()
    db.refresh(user)

    if changes:
        _log_audit(db, admin, "update_user", user.email, "; ".join(changes))

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


@router.get("/apps/{app_id}", response_model=AdminAppDetailResponse)
async def get_app_detail(
    app_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    row = db.query(App, User.email).join(User, App.user_id == User.id).filter(App.id == app_id).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="App not found")
    app, owner_email = row
    return AdminAppDetailResponse(
        id=app.id,
        name=app.name,
        description=app.description,
        status=app.status,
        template_type=app.template_type,
        owner_email=owner_email,
        config=app.config,
        modules=app.modules,
        created_at=app.created_at,
        updated_at=app.updated_at,
    )


@router.put("/apps/{app_id}/status", response_model=AdminAppResponse)
async def update_app_status(
    app_id: int,
    payload: AdminAppStatusUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """Suspende (ou reativa) um app — um app suspenso não fica mais acessível
    publicamente, mesmo que o dono não tenha feito nada (ex: violação de termos)."""
    if payload.status not in _VALID_APP_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status")

    row = db.query(App, User.email).join(User, App.user_id == User.id).filter(App.id == app_id).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="App not found")
    app, owner_email = row

    old_status = app.status
    app.status = payload.status
    db.commit()
    db.refresh(app)

    _log_audit(db, admin, "update_app_status", f"app:{app.id}:{app.name}", f"status: {old_status} -> {payload.status}")

    return AdminAppResponse(
        id=app.id,
        name=app.name,
        status=app.status,
        template_type=app.template_type,
        owner_email=owner_email,
        created_at=app.created_at,
    )


@router.delete("/apps/{app_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_app(
    app_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """Exclui um app definitivamente, limpando as tabelas filhas antes (mesma
    função usada pelo dono em routes/apps.py)."""
    app = db.query(App).filter(App.id == app_id).first()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="App not found")

    app_name = app.name
    delete_app_cascade(db, app_id)
    db.commit()

    _log_audit(db, admin, "delete_app", f"app:{app_id}:{app_name}")
    return None


@router.get("/plans", response_model=list[PlanConfigResponse])
async def list_plans(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    return db.query(PlanConfig).order_by(PlanConfig.price).all()


@router.put("/plans/{plan_name}", response_model=PlanConfigResponse)
async def update_plan(
    plan_name: str,
    payload: PlanConfigUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    plan = db.query(PlanConfig).filter(PlanConfig.plan_name == plan_name).first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")

    changes = []
    for field in ("price", "max_apps", "max_modules", "max_items", "max_categories", "max_push_sends_per_month"):
        value = getattr(payload, field)
        if value is not None and value != getattr(plan, field):
            changes.append(f"{field}: {getattr(plan, field)} -> {value}")
            setattr(plan, field, value)

    db.commit()
    db.refresh(plan)

    if changes:
        _log_audit(db, admin, "update_plan", plan_name, "; ".join(changes))

    return plan


@router.get("/audit-logs", response_model=list[AdminAuditLogResponse])
async def list_audit_logs(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    rows = (
        db.query(AdminAuditLog, User.email)
        .join(User, AdminAuditLog.admin_id == User.id)
        .order_by(AdminAuditLog.created_at.desc())
        .limit(50)
        .all()
    )
    return [
        AdminAuditLogResponse(
            id=log.id,
            admin_id=log.admin_id,
            admin_email=admin_email,
            action=log.action,
            target=log.target,
            details=log.details,
            created_at=log.created_at,
        )
        for log, admin_email in rows
    ]


@router.get("/stats", response_model=AdminStatsResponse)
async def get_stats(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    """Receita mensal recorrente estimada — soma do preço do plano de cada
    usuário ativo, não é faturamento real cobrado (não há acompanhamento de
    cobranças recorrentes de verdade nesta fase)."""
    plans = {p.plan_name: p for p in db.query(PlanConfig).all()}

    users_by_plan: dict = {}
    mrr = 0.0
    for plan_name, count in db.query(User.plan, func.count(User.id)).filter(User.is_active == True).group_by(User.plan).all():  # noqa: E712
        users_by_plan[plan_name] = count
        price = plans[plan_name].price if plan_name in plans else 0
        mrr += price * count

    published_apps = db.query(func.count(App.id)).filter(App.status == "published").scalar()
    total_apps = db.query(func.count(App.id)).scalar()

    return AdminStatsResponse(
        mrr=mrr,
        published_apps=published_apps,
        total_apps=total_apps,
        users_by_plan=users_by_plan,
    )
