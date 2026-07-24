import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_end_user, get_current_user, get_optional_end_user
from app.email_utils import send_email
from app.models import App, AppUser, ModuleItem, Order, OrderItem, User
from app.public_utils import get_published_app
from app.schemas import CartCheckoutRequest, OrderCreate, OrderResponse, OrderUpdate

router = APIRouter(prefix="/api/apps/{app_id}", tags=["orders"])
logger = logging.getLogger("app.orders")


def _notify_owner_new_order(app: App, order: Order, db: Session) -> None:
    owner = db.query(User).filter(User.id == app.user_id).first()
    if not owner:
        return
    try:
        send_email(
            to=owner.email,
            subject=f"Novo pedido em {app.name}",
            html_body=(
                f"<p>Você recebeu um novo pedido pelo módulo <b>{order.module_name}</b> "
                f"no app <b>{app.name}</b>.</p><p>Acesse o painel de Pedidos para ver os detalhes.</p>"
            ),
        )
    except Exception:
        logger.exception("Falha ao enviar e-mail de novo pedido para %s", owner.email)


@router.post("/modules/{module_name}/orders", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    app_id: int,
    module_name: str,
    order_data: OrderCreate,
    db: Session = Depends(get_db),
    end_user: Optional[AppUser] = Depends(get_optional_end_user),
):
    """Cria um pedido a partir de um módulo de formulário/pagamento do app publicado.
    Rota pública — quem envia é o cliente final, não o dono da conta. Se o cliente
    estiver logado (login_cadastro), o pedido é vinculado à conta dele."""
    app = get_published_app(app_id, db)

    order = Order(
        app_id=app_id,
        module_name=module_name,
        end_user_id=end_user.id if end_user else None,
        data=order_data.data,
        amount=order_data.amount,
        payment_method=order_data.payment_method,
        payment_reference=order_data.payment_reference,
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    _notify_owner_new_order(app, order, db)

    return order


@router.post("/modules/{module_name}/cart-checkout", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_cart_checkout(
    app_id: int,
    module_name: str,
    payload: CartCheckoutRequest,
    db: Session = Depends(get_db),
    end_user: Optional[AppUser] = Depends(get_optional_end_user),
):
    """Fecha um pedido a partir do carrinho (itens do cardapio/catalogo). O preço
    e o estoque são sempre conferidos no servidor — nunca confia no que o
    cliente mandou, só em item_id/quantidade."""
    app = get_published_app(app_id, db)

    if not payload.items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Carrinho vazio")

    order_items: List[OrderItem] = []
    subtotal = 0.0
    items_to_decrement: List[tuple[ModuleItem, int]] = []

    for cart_item in payload.items:
        if cart_item.quantity < 1:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Quantidade inválida")

        item = (
            db.query(ModuleItem)
            .filter(
                ModuleItem.id == cart_item.item_id,
                ModuleItem.app_id == app_id,
                ModuleItem.module_name == module_name,
            )
            .first()
        )
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Item {cart_item.item_id} não encontrado")

        if item.stock is not None and item.stock < cart_item.quantity:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Estoque insuficiente para '{item.name}' (disponível: {item.stock})",
            )

        unit_price = item.price or 0.0
        item_subtotal = unit_price * cart_item.quantity
        subtotal += item_subtotal
        order_items.append(
            OrderItem(
                module_item_id=item.id,
                name=item.name,
                unit_price=unit_price,
                quantity=cart_item.quantity,
                subtotal=item_subtotal,
            )
        )
        if item.stock is not None:
            items_to_decrement.append((item, cart_item.quantity))

    order = Order(
        app_id=app_id,
        module_name=module_name,
        end_user_id=end_user.id if end_user else None,
        data=payload.customer,
        amount=subtotal,
        subtotal=subtotal,
        status="pending",
    )
    db.add(order)
    db.flush()

    for order_item in order_items:
        order_item.order_id = order.id
        db.add(order_item)

    for item, qty in items_to_decrement:
        item.stock -= qty

    db.commit()
    db.refresh(order)

    _notify_owner_new_order(app, order, db)

    return order


@router.get("/orders", response_model=List[OrderResponse])
async def list_orders(
    app_id: int,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista todos os pedidos do app (todos os módulos). Só o dono do app pode ver."""
    app = db.query(App).filter(App.id == app_id, App.user_id == current_user.id).first()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="App not found")

    query = db.query(Order).filter(Order.app_id == app_id)
    if status_filter:
        query = query.filter(Order.status == status_filter)

    return query.order_by(Order.created_at.desc()).all()


@router.put("/orders/{order_id}", response_model=OrderResponse)
async def update_order(
    app_id: int,
    order_id: int,
    order_update: OrderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Atualiza o status de um pedido. Só o dono do app pode alterar."""
    app = db.query(App).filter(App.id == app_id, App.user_id == current_user.id).first()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="App not found")

    order = db.query(Order).filter(Order.id == order_id, Order.app_id == app_id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    order.status = order_update.status
    db.commit()
    db.refresh(order)
    return order


@router.get("/my-orders", response_model=List[OrderResponse])
async def list_my_orders(
    app_id: int,
    db: Session = Depends(get_db),
    end_user: AppUser = Depends(get_current_end_user),
):
    """Pedidos do próprio usuário final autenticado."""
    return (
        db.query(Order)
        .filter(Order.app_id == app_id, Order.end_user_id == end_user.id)
        .order_by(Order.created_at.desc())
        .all()
    )
