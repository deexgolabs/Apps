from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.access import get_app_for_read, get_app_for_write
from app.database import get_db
from app.dependencies import get_current_end_user, get_optional_end_user, get_current_user
from app.jobs import enqueue_job
from app.models import App, AppConfig, AppUser, Module, TableReservation, User
from app.public_utils import get_published_app
from app.schemas import ReservationCreate, ReservationResponse, ReservationUpdate
from app.utils import is_within_operating_hours

router = APIRouter(prefix="/api/apps/{app_id}", tags=["reservations"])

VALID_STATUSES = {"pending", "confirmed", "cancelled", "completed"}


def _get_module_settings(app_id: int, module_name: str, db: Session) -> dict:
    row = (
        db.query(AppConfig)
        .join(Module, AppConfig.module_id == Module.id)
        .filter(AppConfig.app_id == app_id, Module.name == module_name)
        .first()
    )
    return row.settings if row and row.settings else {}


def _notify_owner_new_reservation(app: App, reservation: TableReservation, db: Session) -> None:
    owner = db.query(User).filter(User.id == app.user_id).first()
    if not owner:
        return
    when = reservation.reservation_at.strftime("%d/%m/%Y às %H:%M")
    enqueue_job(db, "email", {
        "to": owner.email,
        "subject": f"Nova reserva de mesa em {app.name}",
        "html_body": (
            f"<p>{reservation.customer_name} ({reservation.customer_phone}) pediu uma mesa para "
            f"{reservation.party_size} pessoa(s) em {when}.</p>"
            f"<p>Acesse o painel de Reservas para confirmar.</p>"
        ),
    })


@router.post("/modules/{module_name}/reservations", response_model=ReservationResponse, status_code=status.HTTP_201_CREATED)
async def create_reservation(
    app_id: int,
    module_name: str,
    payload: ReservationCreate,
    db: Session = Depends(get_db),
    end_user: Optional[AppUser] = Depends(get_optional_end_user),
):
    """Cria um pedido de reserva de mesa. Rota pública -- quem envia é o
    cliente final do app publicado, não o dono da conta."""
    app = get_published_app(app_id, db)

    if payload.party_size < 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Número de pessoas inválido")

    reservation_at = payload.reservation_at
    if reservation_at.tzinfo is None:
        reservation_at = reservation_at.replace(tzinfo=timezone.utc)
    if reservation_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A data da reserva precisa ser no futuro")

    settings = _get_module_settings(app_id, module_name, db)
    horario_funcionamento = settings.get("horario_funcionamento")
    if horario_funcionamento and not is_within_operating_hours(horario_funcionamento, reservation_at):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Fora do horário de funcionamento")

    reservation = TableReservation(
        app_id=app_id,
        end_user_id=end_user.id if end_user else None,
        customer_name=payload.customer_name,
        customer_phone=payload.customer_phone,
        party_size=payload.party_size,
        reservation_at=reservation_at,
        notes=payload.notes,
        status="pending",
    )
    db.add(reservation)
    db.commit()
    db.refresh(reservation)

    _notify_owner_new_reservation(app, reservation, db)

    return reservation


@router.get("/my-reservations", response_model=List[ReservationResponse])
async def list_my_reservations(
    app_id: int,
    db: Session = Depends(get_db),
    end_user: AppUser = Depends(get_current_end_user),
):
    """Reservas do próprio usuário final autenticado."""
    return (
        db.query(TableReservation)
        .filter(TableReservation.app_id == app_id, TableReservation.end_user_id == end_user.id)
        .order_by(TableReservation.reservation_at.desc())
        .all()
    )


@router.get("/modules/{module_name}/reservations", response_model=List[ReservationResponse])
async def list_reservations(
    app_id: int,
    module_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista as reservas recebidas. Dono e colaboradores (editor/viewer) podem ver."""
    get_app_for_read(app_id, db, current_user)
    return (
        db.query(TableReservation)
        .filter(TableReservation.app_id == app_id)
        .order_by(TableReservation.reservation_at)
        .all()
    )


@router.put("/reservations/{reservation_id}", response_model=ReservationResponse)
async def update_reservation(
    app_id: int,
    reservation_id: int,
    payload: ReservationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Atualiza status/mesa/observações de uma reserva. Dono e editores podem alterar."""
    get_app_for_write(app_id, db, current_user)

    reservation = db.query(TableReservation).filter(
        TableReservation.id == reservation_id, TableReservation.app_id == app_id
    ).first()
    if not reservation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")

    if payload.status is not None:
        if payload.status not in VALID_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Status inválido. Use um de: {', '.join(sorted(VALID_STATUSES))}.",
            )
        reservation.status = payload.status
    if payload.table_number is not None:
        reservation.table_number = payload.table_number
    if payload.notes is not None:
        reservation.notes = payload.notes

    db.commit()
    db.refresh(reservation)
    return reservation
