import logging
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.email_utils import send_email
from app.models import User
from app.rate_limit import limiter
from app.schemas import (
    UserCreate, UserLogin, Token, UserResponse,
    ForgotPasswordRequest, ResetPasswordRequest,
)
from app.utils import hash_password, verify_password, create_access_token, decode_token

router = APIRouter(prefix="/api/auth", tags=["auth"])
logger = logging.getLogger("app.auth")


def _send_verification_email(user: User) -> None:
    token = create_access_token(
        data={"sub": user.email, "type": "email_verification"},
        expires_delta=timedelta(hours=24),
    )
    link = f"{settings.frontend_url}/auth/verify-email?token={token}"
    try:
        send_email(
            to=user.email,
            subject="Confirme seu e-mail",
            html_body=f"<p>Olá {user.full_name},</p><p>Confirme seu e-mail clicando <a href=\"{link}\">aqui</a>.</p>",
        )
    except Exception:
        logger.exception("Falha ao enviar e-mail de verificação para %s", user.email)


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register(request: Request, user_data: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    db_user = User(
        email=user_data.email,
        full_name=user_data.full_name,
        password_hash=hash_password(user_data.password),
        plan="free"
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    _send_verification_email(db_user)

    access_token = create_access_token(data={"sub": db_user.email})

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse.model_validate(db_user)
    }


@router.post("/login", response_model=Token)
@limiter.limit("5/minute")
async def login(request: Request, user_data: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user_data.email).first()

    if not db_user or not verify_password(user_data.password, db_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    access_token = create_access_token(data={"sub": db_user.email})

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse.model_validate(db_user)
    }


@router.post("/forgot-password")
@limiter.limit("5/minute")
async def forgot_password(request: Request, payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()

    if user:
        token = create_access_token(
            data={"sub": user.email, "type": "password_reset"},
            expires_delta=timedelta(hours=1),
        )
        link = f"{settings.frontend_url}/auth/reset-password?token={token}"
        try:
            send_email(
                to=user.email,
                subject="Redefinição de senha",
                html_body=f"<p>Clique <a href=\"{link}\">aqui</a> para redefinir sua senha. O link expira em 1 hora.</p>",
            )
        except Exception:
            logger.exception("Falha ao enviar e-mail de redefinição de senha para %s", user.email)

    # Resposta genérica sempre, independente do e-mail existir ou não (evita enumeração de contas)
    return {"message": "Se o e-mail existir, um link de redefinição foi enviado."}


@router.post("/reset-password")
async def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    data = decode_token(payload.token)

    if not data or data.get("type") != "password_reset":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token inválido ou expirado")

    user = db.query(User).filter(User.email == data.get("sub")).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token inválido ou expirado")

    user.password_hash = hash_password(payload.new_password)
    db.commit()

    return {"message": "Senha atualizada com sucesso."}


@router.get("/verify-email")
async def verify_email(token: str, db: Session = Depends(get_db)):
    data = decode_token(token)

    if not data or data.get("type") != "email_verification":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token inválido ou expirado")

    user = db.query(User).filter(User.email == data.get("sub")).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token inválido ou expirado")

    user.is_verified = True
    db.commit()

    return {"message": "E-mail verificado com sucesso."}


@router.post("/resend-verification")
async def resend_verification(current_user: User = Depends(get_current_user)):
    if current_user.is_verified:
        return {"message": "E-mail já verificado."}

    _send_verification_email(current_user)
    return {"message": "E-mail de verificação reenviado."}
