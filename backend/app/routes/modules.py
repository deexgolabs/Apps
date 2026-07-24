from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import Module
from app.schemas import ModuleResponse

router = APIRouter(prefix="/api/modules", tags=["modules"])


@router.get("/", response_model=List[ModuleResponse])
async def list_modules(db: Session = Depends(get_db)):
    """Lista todos os módulos disponíveis"""
    modules = db.query(Module).all()
    return modules


@router.get("/{module_id}", response_model=ModuleResponse)
async def get_module(module_id: int, db: Session = Depends(get_db)):
    """Busca módulo específico"""
    module = db.query(Module).filter(Module.id == module_id).first()
    if not module:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Module not found"
        )
    return module
