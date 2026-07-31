import secrets
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models import User
from app.schemas import UserResponse, UserUpdate, ReferralsResponse
from app.dependencies import get_current_user
from app.utils import hash_password

router = APIRouter(prefix="/api/users", tags=["users"])


def _get_or_create_referral_code(user: User, db: Session) -> str:
    if user.referral_code:
        return user.referral_code
    for _ in range(5):
        code = secrets.token_urlsafe(6).replace("_", "").replace("-", "")[:8]
        if not db.query(User).filter(User.referral_code == code).first():
            user.referral_code = code
            db.commit()
            return code
    raise RuntimeError("Não foi possível gerar um código de indicação único")


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/me/referrals", response_model=ReferralsResponse)
async def get_my_referrals(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    code = _get_or_create_referral_code(current_user, db)
    referred = db.query(User).filter(User.referred_by_id == current_user.id).all()

    return ReferralsResponse(
        referral_code=code,
        referral_link=f"{settings.frontend_url}/auth/register?ref={code}",
        bonus_app_slots=current_user.bonus_app_slots,
        referred_count=len(referred),
        activated_count=sum(1 for u in referred if u.is_verified),
        referred=referred,
    )


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
