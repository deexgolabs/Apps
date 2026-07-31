import logging
import secrets
from datetime import timedelta
import pyotp
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
    TwoFactorSetupResponse, TwoFactorEnableRequest, TwoFactorEnableResponse,
    TwoFactorDisableRequest, TwoFactorLoginRequest,
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

    referrer = None
    if user_data.referral_code:
        referrer = db.query(User).filter(User.referral_code == user_data.referral_code).first()

    db_user = User(
        email=user_data.email,
        full_name=user_data.full_name,
        password_hash=hash_password(user_data.password),
        plan="free",
        referred_by_id=referrer.id if referrer else None,
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


@router.post("/login")
@limiter.limit("5/minute")
async def login(request: Request, user_data: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user_data.email).first()

    if not db_user or not verify_password(user_data.password, db_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    if db_user.totp_enabled:
        temp_token = create_access_token(
            data={"sub": db_user.email, "type": "2fa_pending"},
            expires_delta=timedelta(minutes=5),
        )
        return {"requires_2fa": True, "temp_token": temp_token}

    access_token = create_access_token(data={"sub": db_user.email})

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse.model_validate(db_user)
    }


@router.post("/2fa/verify-login", response_model=Token)
@limiter.limit("5/minute")
async def verify_2fa_login(request: Request, payload: TwoFactorLoginRequest, db: Session = Depends(get_db)):
    data = decode_token(payload.temp_token)
    if not data or data.get("type") != "2fa_pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token inválido ou expirado")

    db_user = db.query(User).filter(User.email == data.get("sub")).first()
    if not db_user or not db_user.totp_enabled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token inválido ou expirado")

    valid = bool(db_user.totp_secret) and pyotp.TOTP(db_user.totp_secret).verify(payload.code, valid_window=1)

    if not valid and db_user.totp_recovery_codes:
        for stored_hash in db_user.totp_recovery_codes:
            if verify_password(payload.code, stored_hash):
                valid = True
                db_user.totp_recovery_codes = [h for h in db_user.totp_recovery_codes if h != stored_hash]
                db.commit()
                break

    if not valid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Código inválido")

    access_token = create_access_token(data={"sub": db_user.email})

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse.model_validate(db_user)
    }


@router.post("/2fa/setup", response_model=TwoFactorSetupResponse)
async def setup_2fa(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Gera um novo segredo TOTP (ainda não ativa o 2FA — só após confirmar
    um código válido em /2fa/enable, pra garantir que o dono configurou certo
    o autenticador antes de travar o login atrás dele)."""
    secret = pyotp.random_base32()
    current_user.totp_secret = secret
    db.commit()

    otpauth_url = pyotp.TOTP(secret).provisioning_uri(
        name=current_user.email, issuer_name="Plataforma de Apps"
    )
    return {"secret": secret, "otpauth_url": otpauth_url}


@router.post("/2fa/enable", response_model=TwoFactorEnableResponse)
async def enable_2fa(
    payload: TwoFactorEnableRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not current_user.totp_secret:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Configure o 2FA primeiro em /2fa/setup")

    if not pyotp.TOTP(current_user.totp_secret).verify(payload.code, valid_window=1):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Código inválido")

    recovery_codes = ["-".join([secrets.token_hex(2), secrets.token_hex(2)]) for _ in range(8)]
    current_user.totp_recovery_codes = [hash_password(code) for code in recovery_codes]
    current_user.totp_enabled = True
    db.commit()

    return {"recovery_codes": recovery_codes}


@router.post("/2fa/disable")
async def disable_2fa(
    payload: TwoFactorDisableRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(payload.password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Senha incorreta")

    current_user.totp_enabled = False
    current_user.totp_secret = None
    current_user.totp_recovery_codes = None
    db.commit()

    return {"message": "2FA desativado com sucesso."}


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

    if user.referred_by_id and not user.referral_reward_granted:
        referrer = db.query(User).filter(User.id == user.referred_by_id).first()
        if referrer:
            referrer.bonus_app_slots = (referrer.bonus_app_slots or 0) + 1
            user.referral_reward_granted = True

    db.commit()

    return {"message": "E-mail verificado com sucesso."}


@router.post("/resend-verification")
async def resend_verification(current_user: User = Depends(get_current_user)):
    if current_user.is_verified:
        return {"message": "E-mail já verificado."}

    _send_verification_email(current_user)
    return {"message": "E-mail de verificação reenviado."}
