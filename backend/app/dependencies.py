from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import utcnow
from app.utils import verify_token, decode_token
from app.models import User, AppUser

security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    token = credentials.credentials
    email = verify_token(token)

    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )

    user = db.query(User).filter(User.email == email).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    if user.plan != "free" and user.plan_expires_at and user.plan_expires_at < utcnow():
        user.plan = "free"
        user.plan_expires_at = None
        db.commit()
        db.refresh(user)

    return user


async def get_current_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


async def get_current_end_user(
    app_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> AppUser:
    """Autentica o usuário final de um app publicado (não o dono da conta)."""
    payload = decode_token(credentials.credentials)

    if not payload or payload.get("type") != "end_user" or payload.get("app_id") != app_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )

    end_user = db.query(AppUser).filter(
        AppUser.id == payload.get("end_user_id"),
        AppUser.app_id == app_id
    ).first()

    if not end_user or end_user.deleted_at:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    return end_user


async def get_optional_end_user(
    app_id: int,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security),
    db: Session = Depends(get_db)
) -> Optional[AppUser]:
    """Como get_current_end_user, mas devolve None em vez de 401 quando não há
    token (ou é inválido) — usado em rotas públicas onde login é opcional."""
    if not credentials:
        return None

    payload = decode_token(credentials.credentials)
    if not payload or payload.get("type") != "end_user" or payload.get("app_id") != app_id:
        return None

    end_user = db.query(AppUser).filter(
        AppUser.id == payload.get("end_user_id"),
        AppUser.app_id == app_id
    ).first()
    return end_user if end_user and not end_user.deleted_at else None
