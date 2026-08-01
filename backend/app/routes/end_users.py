from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from typing import List
from app.access import get_app_for_read
from app.config import settings
from app.database import get_db
from app.models import App, AppUser, ItemReview, LoyaltyAccount, ModuleItem, Order, PushSubscription, TableReservation, User, WishlistItem, utcnow
from app.rate_limit import limiter
from app.schemas import (
    EndUserCreate, EndUserDataExport, EndUserLogin, EndUserProfileUpdate, EndUserResponse, EndUserToken,
    OrderResponse, ReservationResponse, ReviewResponse, WishlistItemResponse,
)
from app.utils import hash_password, verify_password, create_access_token
from app.dependencies import get_current_user, get_current_end_user

router = APIRouter(prefix="/api/apps/{app_id}/end-users", tags=["end-users"])

FACEBOOK_OAUTH_VERSION = "v23.0"


def get_or_create_facebook_end_user(
    app_id: int,
    facebook_id: str,
    email: str,
    full_name: str,
    db: Session,
) -> AppUser:
    """Acha o usuário final pelo facebook_id (contas recorrentes) ou pelo e-mail
    (primeira vez logando via Facebook numa conta já criada por e-mail/senha);
    senão cria uma conta nova com auth_provider="facebook" e sem senha.
    Isolado do fluxo OAuth de verdade pra ser testável direto."""
    end_user = db.query(AppUser).filter(AppUser.app_id == app_id, AppUser.facebook_id == facebook_id).first()
    if end_user:
        return end_user

    end_user = db.query(AppUser).filter(AppUser.app_id == app_id, AppUser.email == email).first()
    if end_user:
        end_user.facebook_id = facebook_id
        db.commit()
        db.refresh(end_user)
        return end_user

    end_user = AppUser(
        app_id=app_id,
        email=email,
        full_name=full_name,
        password_hash=None,
        auth_provider="facebook",
        facebook_id=facebook_id,
    )
    db.add(end_user)
    db.commit()
    db.refresh(end_user)
    return end_user


@router.post("/register", response_model=EndUserToken, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register_end_user(request: Request, app_id: int, user_data: EndUserCreate, db: Session = Depends(get_db)):
    """Cadastro de usuário final do app publicado. Rota pública."""
    app = db.query(App).filter(App.id == app_id).first()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="App not found")

    existing = db.query(AppUser).filter(AppUser.app_id == app_id, AppUser.email == user_data.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    end_user = AppUser(
        app_id=app_id,
        email=user_data.email,
        full_name=user_data.full_name,
        password_hash=hash_password(user_data.password),
    )
    db.add(end_user)
    db.commit()
    db.refresh(end_user)

    access_token = create_access_token(data={"end_user_id": end_user.id, "app_id": app_id, "type": "end_user"})

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": EndUserResponse.model_validate(end_user)
    }


@router.post("/login", response_model=EndUserToken)
@limiter.limit("5/minute")
async def login_end_user(request: Request, app_id: int, credentials: EndUserLogin, db: Session = Depends(get_db)):
    """Login de usuário final do app publicado. Rota pública."""
    end_user = db.query(AppUser).filter(AppUser.app_id == app_id, AppUser.email == credentials.email).first()

    if not end_user or not end_user.password_hash or not verify_password(credentials.password, end_user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    access_token = create_access_token(data={"end_user_id": end_user.id, "app_id": app_id, "type": "end_user"})

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": EndUserResponse.model_validate(end_user)
    }


@router.get("/facebook/login-url")
async def facebook_login_url(app_id: int, db: Session = Depends(get_db)):
    """Devolve a URL de autorização do Facebook pro app publicado. Rota pública."""
    app = db.query(App).filter(App.id == app_id, App.status == "published").first()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="App not found or not published")

    if not settings.facebook_app_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Login via Facebook não configurado nesta instância")

    redirect_uri = f"{settings.backend_url}/api/end-users/facebook/callback"
    params = {
        "client_id": settings.facebook_app_id,
        "redirect_uri": redirect_uri,
        "state": str(app_id),
        "scope": "email,public_profile",
    }
    url = f"https://www.facebook.com/{FACEBOOK_OAUTH_VERSION}/dialog/oauth?{urlencode(params)}"
    return {"url": url}


@router.get("/me", response_model=EndUserResponse)
async def get_current_end_user_info(end_user: AppUser = Depends(get_current_end_user)):
    """Devolve os dados do usuário final autenticado (usado pra restaurar a sessão
    após o redirect do login via Facebook, que só traz o token na URL)."""
    return end_user


@router.put("/me", response_model=EndUserResponse)
async def update_current_end_user_profile(
    app_id: int,
    payload: EndUserProfileUpdate,
    db: Session = Depends(get_db),
    end_user: AppUser = Depends(get_current_end_user),
):
    """Atualiza nome/telefone/endereço do próprio usuário final, e opcionalmente
    a senha (exige a senha atual). Usado pra pré-preencher o checkout depois."""
    if payload.full_name is not None:
        end_user.full_name = payload.full_name
    if payload.phone is not None:
        end_user.phone = payload.phone
    if payload.address is not None:
        end_user.address = payload.address

    if payload.new_password:
        if not end_user.password_hash or not payload.current_password or not verify_password(
            payload.current_password, end_user.password_hash
        ):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Senha atual incorreta")
        end_user.password_hash = hash_password(payload.new_password)

    db.commit()
    db.refresh(end_user)
    return end_user


@router.get("/me/export", response_model=EndUserDataExport)
async def export_my_data(
    app_id: int,
    db: Session = Depends(get_db),
    end_user: AppUser = Depends(get_current_end_user),
):
    """LGPD — devolve tudo que identifica o cliente final nesta loja, pra ele
    baixar (direito de portabilidade/acesso aos próprios dados)."""
    orders = (
        db.query(Order)
        .filter(Order.app_id == app_id, Order.end_user_id == end_user.id)
        .order_by(Order.created_at.desc())
        .all()
    )
    reviews = (
        db.query(ItemReview)
        .join(ModuleItem, ModuleItem.id == ItemReview.item_id)
        .filter(ModuleItem.app_id == app_id, ItemReview.end_user_id == end_user.id)
        .all()
    )
    wishlist = (
        db.query(WishlistItem)
        .filter(WishlistItem.app_id == app_id, WishlistItem.end_user_id == end_user.id)
        .all()
    )
    loyalty = (
        db.query(LoyaltyAccount)
        .filter(LoyaltyAccount.app_id == app_id, LoyaltyAccount.end_user_id == end_user.id)
        .first()
    )
    reservations = (
        db.query(TableReservation)
        .filter(TableReservation.app_id == app_id, TableReservation.end_user_id == end_user.id)
        .order_by(TableReservation.reservation_at.desc())
        .all()
    )

    return EndUserDataExport(
        profile=EndUserResponse.model_validate(end_user),
        orders=[OrderResponse.model_validate(o) for o in orders],
        reservations=[ReservationResponse.model_validate(r) for r in reservations],
        reviews=[
            ReviewResponse(
                id=r.id,
                item_id=r.item_id,
                end_user_id=r.end_user_id,
                end_user_name=end_user.full_name,
                rating=r.rating,
                comment=r.comment,
                created_at=r.created_at,
            )
            for r in reviews
        ],
        wishlist=[WishlistItemResponse.model_validate(w) for w in wishlist],
        loyalty_points=loyalty.points if loyalty else 0,
    )


@router.delete("/me")
async def delete_my_account(
    app_id: int,
    db: Session = Depends(get_db),
    end_user: AppUser = Depends(get_current_end_user),
):
    """LGPD — anonimiza os dados pessoais do cliente final e apaga o que não
    precisa ser retido. Pedidos ficam (retenção fiscal/legal do lojista), mas
    já sem PII identificável, já que o AppUser vinculado foi anonimizado."""
    db.query(WishlistItem).filter(
        WishlistItem.app_id == app_id, WishlistItem.end_user_id == end_user.id
    ).delete(synchronize_session=False)
    db.query(PushSubscription).filter(
        PushSubscription.app_id == app_id, PushSubscription.end_user_id == end_user.id
    ).delete(synchronize_session=False)
    db.query(LoyaltyAccount).filter(
        LoyaltyAccount.app_id == app_id, LoyaltyAccount.end_user_id == end_user.id
    ).delete(synchronize_session=False)

    end_user.full_name = "Usuário removido"
    end_user.email = f"removido-{end_user.id}@deleted.local"
    end_user.phone = None
    end_user.address = None
    end_user.password_hash = None
    end_user.facebook_id = None
    end_user.deleted_at = utcnow()
    db.commit()

    return {"message": "Sua conta e dados pessoais foram removidos."}


@router.get("/", response_model=List[EndUserResponse])
async def list_end_users(
    app_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lista os usuários finais cadastrados no app. Só quem tem acesso ao app pode ver."""
    get_app_for_read(app_id, db, current_user)

    return db.query(AppUser).filter(AppUser.app_id == app_id).order_by(AppUser.created_at.desc()).all()
