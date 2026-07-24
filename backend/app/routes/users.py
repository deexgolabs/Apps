from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.schemas import UserResponse, UserUpdate
from app.dependencies import get_current_user
from app.utils import hash_password

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_me(
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if user_data.full_name:
        current_user.full_name = user_data.full_name
    if user_data.password:
        current_user.password_hash = hash_password(user_data.password)

    db.commit()
    db.refresh(current_user)
    return current_user
