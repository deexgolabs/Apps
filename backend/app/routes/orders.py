import csv
import io
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.constants import ORDER_STATUS_LABELS
from app.database import get_db
from app.dependencies import get_current_end_user, get_current_user, get_optional_end_user
from app.email_utils import send_email
from app.models import App, AppConfig, AppUser, ItemVariation, Module, ModuleItem, Order, OrderItem, OrderStatusEvent, User
from app.payment_gateways import (
    checkout_mercado_pago,
    checkout_pagseguro,
    checkout_paypal,
    verify_mercado_pago,
    verify_pagseguro,
    verify_paypal,
)
from app.public_utils import get_published_app
from app.routes.coupons import validate_coupon
from app.routes.push import send_push_to_end_user
from app.schemas import (
    CartCheckoutRequest,
    CloseTableRequest,
    OrderCreate,
    OrderResponse,
    OrderUpdate,
    SalesReportProduct,
    SalesReportResponse,
)
from app.utils import compute_frete, is_within_operating_hours

GATEWAY_MODULES = {"mercado_pago", "paypal", "pagseguro"}

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


def _record_status_event(order: Order, db: Session) -> None:
    """Registra o status atual do pedido na linha do tempo. Chamado na criação
    (status inicial) e em toda mudança de status feita pelo dono ou pelo
    cliente (cancelamento)."""
    db.add(OrderStatusEvent(order_id=order.id, status=order.status))


def _notify_owner_order_cancelled(app: App, order: Order, db: Session) -> None:
    owner = db.query(User).filter(User.id == app.user_id).first()
    if not owner:
        return
    try:
        send_email(
            to=owner.email,
            subject=f"Pedido cancelado pelo cliente em {app.name}",
            html_body=f"<p>O cliente cancelou o pedido #{order.id} ({order.module_name}) antes do preparo.</p>",
        )
    except Exception:
        logger.exception("Falha ao enviar e-mail de cancelamento para %s", owner.email)


def _get_module_settings(app_id: int, module_name: str, db: Session) -> dict:
    row = (
        db.query(AppConfig)
        .join(Module, AppConfig.module_id == Module.id)
        .filter(AppConfig.app_id == app_id, Module.name == module_name)
        .first()
    )
    return row.settings if row and row.settings else {}


async def _start_gateway_checkout(gateway: str, settings: dict, valor: float, titulo: str, order_id: int) -> tuple[str | None, str | None]:
    """Abre uma cobrança na gateway pelo valor real do carrinho — diferente do
    fluxo de módulo de pagamento avulso (routes/payments.py), que usa um valor
    fixo configurado nas settings. Devolve (checkout_url, payment_reference)."""
    if gateway == "mercado_pago":
        access_token = settings.get("access_token")
        if not access_token:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Módulo não configurado: falta o access_token do Mercado Pago")
        result = await checkout_mercado_pago(valor, titulo, access_token, external_reference=str(order_id))
        return result.get("checkout_url"), str(order_id)
    if gateway == "paypal":
        client_id = settings.get("client_id")
        client_secret = settings.get("client_secret")
        if not client_id or not client_secret:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Módulo não configurado: falta o client_id/client_secret do PayPal")
        result = await checkout_paypal(str(valor), titulo, client_id, client_secret)
        return result.get("checkout_url"), result.get("gateway_order_id")
    if gateway == "pagseguro":
        token = settings.get("token")
        if not token:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Módulo não configurado: falta o token do PagSeguro")
        result = await checkout_pagseguro(valor, titulo, token)
        return result.get("checkout_url"), result.get("gateway_order_id")
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Gateway de pagamento inválida")


async def _verify_gateway_payment(gateway: str, settings: dict, payment_reference: str) -> bool:
    if gateway == "mercado_pago":
        return await verify_mercado_pago(payment_reference, settings.get("access_token"))
    if gateway == "paypal":
        return await verify_paypal(payment_reference, settings.get("client_id"), settings.get("client_secret"))
    if gateway == "pagseguro":
        return await verify_pagseguro(payment_reference, settings.get("token"))
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Gateway de pagamento inválida")


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
    db.flush()
    _record_status_event(order, db)
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

    if payload.gateway and payload.gateway not in GATEWAY_MODULES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Gateway de pagamento inválida")

    order_items: List[OrderItem] = []
    subtotal = 0.0
    items_to_decrement: List[tuple] = []

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

        # variation_ids (plural) é o combo de grupos combináveis (Fase D) — ex:
        # tamanho + sabor, uma opção por grupo, preço de cada uma somado como
        # delta ao preço base. variation_id (singular) continua servindo o
        # fluxo antigo de variação única com preço absoluto, sem grupo.
        selected_ids = list(dict.fromkeys(cart_item.variation_ids or ([cart_item.variation_id] if cart_item.variation_id else [])))
        selected_variations: List[ItemVariation] = []
        if selected_ids:
            selected_variations = (
                db.query(ItemVariation)
                .filter(ItemVariation.id.in_(selected_ids), ItemVariation.item_id == item.id)
                .all()
            )
            if len(selected_variations) != len(selected_ids):
                found_ids = {v.id for v in selected_variations}
                missing = next(i for i in selected_ids if i not in found_ids)
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Variação {missing} não encontrada")

            seen_groups: dict = {}
            for v in selected_variations:
                if v.group_name is not None:
                    if v.group_name in seen_groups:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Só é possível escolher uma opção do grupo '{v.group_name}'",
                        )
                    seen_groups[v.group_name] = v.id

        is_combo = len(selected_variations) > 1 or any(v.group_name is not None for v in selected_variations)

        for v in selected_variations:
            if v.stock is not None and v.stock < cart_item.quantity:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Estoque insuficiente para '{item.name} ({v.name})' (disponível: {v.stock})",
                )

        if is_combo:
            unit_price = (item.price or 0.0) + sum(v.price for v in selected_variations)
            item_name = f"{item.name} ({', '.join(v.name for v in selected_variations)})" if selected_variations else item.name
        elif selected_variations:
            unit_price = selected_variations[0].price or 0.0
            item_name = f"{item.name} ({selected_variations[0].name})"
        else:
            unit_price = item.price or 0.0
            item_name = item.name

        if not selected_variations and item.stock is not None and item.stock < cart_item.quantity:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Estoque insuficiente para '{item_name}' (disponível: {item.stock})",
            )

        item_subtotal = unit_price * cart_item.quantity
        subtotal += item_subtotal
        order_items.append(
            OrderItem(
                module_item_id=item.id,
                item_variation_id=selected_variations[0].id if len(selected_variations) == 1 else None,
                name=item_name,
                unit_price=unit_price,
                quantity=cart_item.quantity,
                subtotal=item_subtotal,
            )
        )
        for v in selected_variations:
            if v.stock is not None:
                items_to_decrement.append((v, cart_item.quantity))
        if not selected_variations and item.stock is not None:
            items_to_decrement.append((item, cart_item.quantity))

    entrega_settings = _get_module_settings(app_id, "pagamento_entrega", db)

    valor_minimo = entrega_settings.get("valor_minimo_pedido")
    if valor_minimo:
        try:
            if subtotal < float(valor_minimo):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Pedido mínimo de R$ {float(valor_minimo):.2f}",
                )
        except ValueError:
            pass

    horario_funcionamento = entrega_settings.get("horario_funcionamento")
    if horario_funcionamento and not is_within_operating_hours(horario_funcionamento, datetime.now(timezone.utc)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Fora do horário de funcionamento")

    delivery_fee = 0.0
    if payload.fulfillment_type == "delivery":
        frete_settings = _get_module_settings(app_id, "calculo_frete", db)
        delivery_fee = compute_frete(frete_settings.get("regras", ""), payload.cep)

    discount_amount = 0.0
    coupon = None
    coupon_code = payload.coupon_code.strip().upper() if payload.coupon_code else None
    if coupon_code:
        coupon, discount_amount, reason = validate_coupon(app_id, coupon_code, subtotal, db)
        if not coupon:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=reason or "Cupom inválido")

    total = subtotal + delivery_fee - discount_amount

    order = Order(
        app_id=app_id,
        module_name=module_name,
        end_user_id=end_user.id if end_user else None,
        data=payload.customer,
        amount=total,
        subtotal=subtotal,
        delivery_fee=delivery_fee,
        discount_amount=discount_amount,
        coupon_code=coupon.code if coupon else None,
        fulfillment_type=payload.fulfillment_type,
        table_number=payload.table_number if payload.fulfillment_type == "dine_in" else None,
        payment_method=payload.gateway,
        status="pending",
    )
    db.add(order)
    db.flush()
    _record_status_event(order, db)

    for order_item in order_items:
        order_item.order_id = order.id
        db.add(order_item)

    for item, qty in items_to_decrement:
        item.stock -= qty

    if coupon:
        coupon.uses_count += 1

    db.commit()
    db.refresh(order)

    _notify_owner_new_order(app, order, db)

    checkout_url = None
    if payload.gateway:
        gateway_settings = _get_module_settings(app_id, payload.gateway, db)
        checkout_url, payment_reference = await _start_gateway_checkout(
            payload.gateway, gateway_settings, total, app.name, order.id
        )
        order.payment_reference = payment_reference
        db.commit()
        db.refresh(order)

    order.checkout_url = checkout_url
    return order


@router.post("/orders/{order_id}/confirm-payment", response_model=OrderResponse)
async def confirm_cart_order_payment(app_id: int, order_id: int, db: Session = Depends(get_db)):
    """Consulta a gateway configurada pro pedido (guardada em payment_method na
    hora do checkout) e confirma o pagamento, igual ao fluxo de módulo de
    pagamento avulso — mas aqui pro pedido feito pelo carrinho. Rota pública,
    chamada pelo cliente final depois de voltar do checkout da gateway."""
    order = db.query(Order).filter(Order.id == order_id, Order.app_id == app_id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    if not order.payment_method or order.payment_method not in GATEWAY_MODULES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Este pedido não usa pagamento por gateway")

    if order.status != "confirmed":
        settings = _get_module_settings(app_id, order.payment_method, db)
        approved = await _verify_gateway_payment(order.payment_method, settings, order.payment_reference)
        if approved:
            app = db.query(App).filter(App.id == app_id).first()
            order.status = "confirmed"
            _record_status_event(order, db)
            db.commit()
            db.refresh(order)
            _notify_customer_status_change(app, order, db)

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


def _notify_customer_status_change(app: App, order: Order, db: Session) -> None:
    """Avisa o cliente final (se logado) que o status do pedido mudou —
    e-mail + push dedicado, cada um best-effort e isolado, nunca conta no
    limite mensal de push (é notificação individual, não campanha)."""
    if not order.end_user_id:
        return
    label = ORDER_STATUS_LABELS.get(order.status, order.status)
    end_user = db.query(AppUser).filter(AppUser.id == order.end_user_id).first()
    if end_user:
        try:
            send_email(
                to=end_user.email,
                subject=f"Pedido atualizado: {label}",
                html_body=f"<p>Seu pedido em <b>{app.name}</b> agora está: <b>{label}</b>.</p>",
            )
        except Exception:
            logger.exception("Falha ao enviar e-mail de status pro cliente %s", end_user.email)
    try:
        send_push_to_end_user(app.id, order.end_user_id, f"Pedido {label}", f"Seu pedido em {app.name} agora está {label.lower()}.", db)
    except Exception:
        logger.exception("Falha ao enviar push de status pro end_user %s", order.end_user_id)


@router.put("/orders/close-table", response_model=List[OrderResponse])
async def close_table(
    app_id: int,
    payload: CloseTableRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fecha em lote todos os pedidos em aberto de uma mesa/comanda, marcando
    como completed — dispara os mesmos hooks de notificação por pedido.
    Precisa vir registrada antes de PUT /orders/{order_id} nesse arquivo,
    senão o Starlette casa 'close-table' com o path param order_id (int) e
    devolve 422 antes de chegar aqui."""
    app = db.query(App).filter(App.id == app_id, App.user_id == current_user.id).first()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="App not found")

    orders = (
        db.query(Order)
        .filter(
            Order.app_id == app_id,
            Order.table_number == payload.table_number,
            Order.status.notin_(["completed", "cancelled"]),
        )
        .all()
    )
    if not orders:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nenhum pedido em aberto para essa mesa")

    for order in orders:
        order.status = "completed"
        _record_status_event(order, db)
    db.commit()

    for order in orders:
        db.refresh(order)
        _notify_customer_status_change(app, order, db)

    return orders


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

    if order_update.status != order.status:
        order.status = order_update.status
        _record_status_event(order, db)
    db.commit()
    db.refresh(order)

    _notify_customer_status_change(app, order, db)
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


CANCELABLE_STATUSES = {"pending", "confirmed"}


@router.put("/my-orders/{order_id}/cancel", response_model=OrderResponse)
async def cancel_my_order(
    app_id: int,
    order_id: int,
    db: Session = Depends(get_db),
    end_user: AppUser = Depends(get_current_end_user),
):
    """Cliente final cancela o próprio pedido, só permitido enquanto ainda não
    entrou em preparo (pending/confirmed) — depois disso já pode ter custo
    real pro lojista, então cancelamento passa a ser só pelo dono."""
    order = (
        db.query(Order)
        .filter(Order.id == order_id, Order.app_id == app_id, Order.end_user_id == end_user.id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    if order.status not in CANCELABLE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Esse pedido já está em preparo e não pode mais ser cancelado pelo cliente",
        )

    app = db.query(App).filter(App.id == app_id).first()

    order.status = "cancelled"
    _record_status_event(order, db)
    db.commit()
    db.refresh(order)

    _notify_owner_order_cancelled(app, order, db)
    return order


def _get_owned_app(app_id: int, db: Session, current_user: User) -> App:
    app = db.query(App).filter(App.id == app_id, App.user_id == current_user.id).first()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="App not found")
    return app


@router.get("/orders/report", response_model=SalesReportResponse)
async def get_sales_report(
    app_id: int,
    days: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Receita (só pedidos completed), contagem por status e top-10 produtos —
    opcionalmente filtrado aos últimos `days` dias. Só o dono do app pode ver."""
    _get_owned_app(app_id, db, current_user)

    query = db.query(Order).filter(Order.app_id == app_id)
    if days:
        query = query.filter(Order.created_at >= datetime.now(timezone.utc) - timedelta(days=days))
    orders = query.all()

    revenue = sum(o.amount or 0 for o in orders if o.status == "completed")
    orders_by_status: dict = {}
    for o in orders:
        orders_by_status[o.status] = orders_by_status.get(o.status, 0) + 1

    order_ids = [o.id for o in orders]
    top_products: List[SalesReportProduct] = []
    if order_ids:
        rows = (
            db.query(
                OrderItem.name,
                func.sum(OrderItem.quantity).label("quantity"),
                func.sum(OrderItem.subtotal).label("revenue"),
            )
            .filter(OrderItem.order_id.in_(order_ids))
            .group_by(OrderItem.name)
            .order_by(func.sum(OrderItem.quantity).desc())
            .limit(10)
            .all()
        )
        top_products = [SalesReportProduct(name=r.name, quantity=r.quantity, revenue=r.revenue) for r in rows]

    return SalesReportResponse(revenue=revenue, orders_by_status=orders_by_status, top_products=top_products)


@router.get("/orders/export.csv")
async def export_orders_csv(
    app_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Exporta todos os pedidos do app em CSV — um pedido por linha, com um
    resumo dos itens. Só o dono do app pode exportar."""
    _get_owned_app(app_id, db, current_user)

    orders = db.query(Order).filter(Order.app_id == app_id).order_by(Order.created_at.desc()).all()

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        "id", "modulo", "status", "criado_em", "itens", "subtotal", "frete",
        "desconto", "total", "forma_entrega", "mesa", "cupom", "dados_cliente",
    ])
    for o in orders:
        items_summary = "; ".join(f"{oi.quantity}x {oi.name}" for oi in o.items)
        writer.writerow([
            o.id,
            o.module_name,
            ORDER_STATUS_LABELS.get(o.status, o.status),
            o.created_at.isoformat(),
            items_summary,
            o.subtotal if o.subtotal is not None else "",
            o.delivery_fee if o.delivery_fee is not None else "",
            o.discount_amount if o.discount_amount is not None else "",
            o.amount if o.amount is not None else "",
            o.fulfillment_type or "",
            o.table_number or "",
            o.coupon_code or "",
            "; ".join(f"{k}: {v}" for k, v in (o.data or {}).items()),
        ])
    buffer.seek(0)

    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=pedidos_app_{app_id}.csv"},
    )


