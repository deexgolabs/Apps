from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from typing import Optional
from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expiration_hours)

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm
    )

    return encoded_jwt


def verify_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm]
        )
        email: str = payload.get("sub")
        return email
    except JWTError:
        return None


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm]
        )
    except JWTError:
        return None


def compute_frete(regras_text: str, cep: Optional[str]) -> float:
    """Porta em Python da mesma lógica do FreteCalculator no frontend (prefixo
    de CEP : preço, um por linha) — primeira regra cujo prefixo bate com o CEP
    (não é o de maior prefixo, é o primeiro da lista, igual ao .find do JS).
    Sem CEP ou sem regra configurada/batendo, o frete é 0."""
    if not cep:
        return 0.0
    for line in (regras_text or "").split("\n"):
        line = line.strip()
        if not line or ":" not in line:
            continue
        prefix, _, price_str = line.partition(":")
        prefix = prefix.strip()
        try:
            price = float(price_str.strip())
        except ValueError:
            continue
        if prefix and cep.startswith(prefix):
            return price
    return 0.0


_WEEKDAY_ALIASES = {
    "dom": 6, "seg": 0, "ter": 1, "qua": 2, "qui": 3, "sex": 4, "sab": 5, "sáb": 5,
}


def _parse_day_range(token: str) -> Optional[list[int]]:
    token = token.strip().lower()
    if "-" in token:
        start_s, _, end_s = token.partition("-")
        start, end = _WEEKDAY_ALIASES.get(start_s.strip()), _WEEKDAY_ALIASES.get(end_s.strip())
        if start is None or end is None:
            return None
        if start <= end:
            return list(range(start, end + 1))
        return list(range(start, 7)) + list(range(0, end + 1))
    day = _WEEKDAY_ALIASES.get(token)
    return [day] if day is not None else None


def is_within_operating_hours(horario_text: str, now: datetime) -> bool:
    """Formato: 'dia:abre-fecha' por linha (ex: 'seg-sex:08:00-18:00'), dia
    aceita intervalo ou dia único, dias da semana em PT-BR abreviado. Sem
    configuração (texto vazio), considera sempre aberto."""
    if not (horario_text or "").strip():
        return True

    weekday = now.weekday()  # segunda=0 ... domingo=6, igual ao _WEEKDAY_ALIASES
    current_minutes = now.hour * 60 + now.minute

    for line in horario_text.split("\n"):
        line = line.strip()
        if not line or ":" not in line:
            continue
        day_part, _, hours_part = line.partition(":")
        days = _parse_day_range(day_part)
        if not days or weekday not in days:
            continue
        hours_part = hours_part.strip()
        if "-" not in hours_part:
            continue
        open_s, _, close_s = hours_part.partition("-")
        try:
            open_h, open_m = (int(x) for x in open_s.strip().split(":"))
            close_h, close_m = (int(x) for x in close_s.strip().split(":"))
        except ValueError:
            continue
        open_minutes = open_h * 60 + open_m
        close_minutes = close_h * 60 + close_m
        if open_minutes <= current_minutes <= close_minutes:
            return True

    return False


def log_owner_action(
    db: Session,
    owner_id: int,
    action: str,
    target: str,
    app_id: Optional[int] = None,
    details: Optional[str] = None,
) -> None:
    """Registra uma ação do dono no próprio log de auditoria (rotas chamam isso
    depois de já ter dado commit na mudança em si, pra log não travar a ação
    principal se algo desse errado -- mas na prática é só um insert simples)."""
    from app.models import OwnerAuditLog

    db.add(OwnerAuditLog(owner_id=owner_id, app_id=app_id, action=action, target=target, details=details))
    db.commit()


def delete_app_cascade(db: Session, app_id: int) -> None:
    """Apaga um app e todas as tabelas filhas na ordem certa de FK — usado tanto
    pelo dono (routes/apps.py) quanto pelo admin (routes/admin.py), já que as
    tabelas não têm ON DELETE CASCADE no banco. Não dá commit, quem chama decide
    quando commitar (ou pode fazer mais coisa antes, como log de auditoria)."""
    from app.models import (
        AbandonedCart,
        App,
        AppCollaborator,
        Campaign,
        AppConfig,
        AppUser,
        AppVersion,
        Coupon,
        FormSubmission,
        ItemReview,
        ItemVariation,
        LoyaltyAccount,
        ModuleCategory,
        ModuleItem,
        Order,
        OrderItem,
        OrderStatusEvent,
        OwnerAuditLog,
        PushSendLog,
        PushSubscription,
        TableReservation,
        WebhookSubscription,
        WishlistItem,
    )

    item_ids = [row.id for row in db.query(ModuleItem.id).filter(ModuleItem.app_id == app_id).all()]
    order_ids = [row.id for row in db.query(Order.id).filter(Order.app_id == app_id).all()]

    if order_ids:
        db.query(OrderStatusEvent).filter(OrderStatusEvent.order_id.in_(order_ids)).delete(synchronize_session=False)
        db.query(OrderItem).filter(OrderItem.order_id.in_(order_ids)).delete(synchronize_session=False)
    if item_ids:
        db.query(ItemReview).filter(ItemReview.item_id.in_(item_ids)).delete(synchronize_session=False)
        db.query(ItemVariation).filter(ItemVariation.item_id.in_(item_ids)).delete(synchronize_session=False)
    db.query(Order).filter(Order.app_id == app_id).delete(synchronize_session=False)
    db.query(FormSubmission).filter(FormSubmission.app_id == app_id).delete(synchronize_session=False)
    db.query(PushSendLog).filter(PushSendLog.app_id == app_id).delete(synchronize_session=False)
    db.query(PushSubscription).filter(PushSubscription.app_id == app_id).delete(synchronize_session=False)
    db.query(Coupon).filter(Coupon.app_id == app_id).delete(synchronize_session=False)
    db.query(TableReservation).filter(TableReservation.app_id == app_id).delete(synchronize_session=False)
    db.query(AbandonedCart).filter(AbandonedCart.app_id == app_id).delete(synchronize_session=False)
    db.query(Campaign).filter(Campaign.app_id == app_id).delete(synchronize_session=False)
    db.query(WebhookSubscription).filter(WebhookSubscription.app_id == app_id).delete(synchronize_session=False)
    db.query(AppCollaborator).filter(AppCollaborator.app_id == app_id).delete(synchronize_session=False)
    db.query(LoyaltyAccount).filter(LoyaltyAccount.app_id == app_id).delete(synchronize_session=False)
    db.query(WishlistItem).filter(WishlistItem.app_id == app_id).delete(synchronize_session=False)
    db.query(ModuleItem).filter(ModuleItem.app_id == app_id).delete(synchronize_session=False)
    db.query(ModuleCategory).filter(ModuleCategory.app_id == app_id).delete(synchronize_session=False)
    db.query(AppUser).filter(AppUser.app_id == app_id).delete(synchronize_session=False)
    db.query(AppConfig).filter(AppConfig.app_id == app_id).delete(synchronize_session=False)
    db.query(AppVersion).filter(AppVersion.app_id == app_id).delete(synchronize_session=False)
    # Mantém as entradas do log de auditoria (inclusive a do próprio "delete_app"),
    # só desvincula do app que está deixando de existir -- mesmo raciocínio de
    # preservar registro já usado pra Order na exclusão de conta (LGPD).
    db.query(OwnerAuditLog).filter(OwnerAuditLog.app_id == app_id).update(
        {OwnerAuditLog.app_id: None}, synchronize_session=False
    )
    db.query(App).filter(App.id == app_id).delete(synchronize_session=False)
