from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import App, User
from app.schemas import AppCreate, AppResponse, AppUpdate
from app.dependencies import get_current_user
from app.constants import PLAN_LIMITS, APP_TEMPLATES

router = APIRouter(prefix="/api/apps", tags=["apps"])


@router.get("/", response_model=List[AppResponse])
async def list_apps(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lista todos os apps do usuário"""
    apps = db.query(App).filter(App.user_id == current_user.id).all()
    return apps


@router.post("/", response_model=AppResponse, status_code=status.HTTP_201_CREATED)
async def create_app(
    app_data: AppCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cria novo app, respeitando o limite de apps do plano do usuário"""
    limit = PLAN_LIMITS.get(current_user.plan, PLAN_LIMITS["free"])["apps"]
    if limit is not None:
        current_count = db.query(App).filter(App.user_id == current_user.id).count()
        if current_count >= limit:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Limite de {limit} app(s) atingido para o plano '{current_user.plan}'. Faça upgrade para criar mais."
            )

    template = APP_TEMPLATES.get(app_data.template_type, {})
    module_limit = PLAN_LIMITS.get(current_user.plan, PLAN_LIMITS["free"])["modules"]

    # Config enviada no wizard (cores/logo customizados) sobrescreve o padrão do
    # template, mas não substitui o dict inteiro — só as chaves informadas.
    config = {**template.get("config", {}), **(app_data.config or {})}

    db_app = App(
        user_id=current_user.id,
        name=app_data.name,
        description=app_data.description,
        template_type=app_data.template_type,
        status="draft",
        config=config,
        modules=list(template.get("modules", []))[:module_limit]
    )
    db.add(db_app)
    db.commit()
    db.refresh(db_app)
    return db_app


@router.get("/{app_id}", response_model=AppResponse)
async def get_app(
    app_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Busca app específico"""
    app = db.query(App).filter(
        App.id == app_id,
        App.user_id == current_user.id
    ).first()

    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="App not found"
        )

    return app


@router.put("/{app_id}", response_model=AppResponse)
async def update_app(
    app_id: int,
    app_data: AppUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Atualiza app"""
    app = db.query(App).filter(
        App.id == app_id,
        App.user_id == current_user.id
    ).first()

    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="App not found"
        )

    if app_data.name is not None:
        app.name = app_data.name
    if app_data.description is not None:
        app.description = app_data.description
    if app_data.config is not None:
        app.config = app_data.config
    if app_data.modules is not None:
        module_limit = PLAN_LIMITS.get(current_user.plan, PLAN_LIMITS["free"])["modules"]
        if len(app_data.modules) > module_limit:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Limite de {module_limit} módulo(s) atingido para o plano '{current_user.plan}'. Faça upgrade para ativar mais."
            )
        app.modules = app_data.modules
    if app_data.status is not None:
        app.status = app_data.status

    db.commit()
    db.refresh(app)
    return app


@router.delete("/{app_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_app(
    app_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Deleta app"""
    app = db.query(App).filter(
        App.id == app_id,
        App.user_id == current_user.id
    ).first()

    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="App not found"
        )

    db.delete(app)
    db.commit()
    return None
