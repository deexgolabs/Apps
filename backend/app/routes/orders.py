import csv
import io
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.access import get_app_for_read, get_app_for_write
from app.auto_coupons import check_and_issue_purchase_coupons
from app.constants import ORDER_STATUS_LABELS
from app.database import get_db
from app.dependencies import get_current_end_user, get_current_user, get_optional_end_user
from app.jobs import enqueue_job
from app.webhook_dispatch import dispatch_webhook_event
from app.models import AbandonedCart, App, AppConfig, AppUser, ItemVariation, LoyaltyAccount, Module, ModuleItem, Order, OrderItem, OrderStatusEvent, User
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
from app.schemas import (
    CartCheckoutRequest,
    CloseTableRequest,
    FinancialBreakdownItem,
    FinancialReportResponse,
    OrderCreate,
    OrderResponse,
    OrderUpdate,
    SalesReportProduct,
    SalesReportResponse,
)
from app.utils import compute_frete, is_within_operating_hours, log_owner_action

GATEWAY_MODULES = {"mercado_pago", "paypal", "pagseguro"}

router = APIRouter(prefix="/api/apps/{app_id}", tags=["orders"])


def _notify_owner_new_order(app: App, order: Order, db: Session) -> None:
    owner = db.query(User).filter(User.id == app.user_id).first()
    if not owner:
        return
    enqueue_job(db, "email", {
        "to": owner.email,
        "subject": f"Novo pedido em {app.name}",
        "html_body": (
            f"<p>Você recebeu um novo pedido pelo módulo <b>{order.module_name}</b> "
            f"no app <b>{app.name}</b>.</p><p>Acesse o painel de Pedidos para ver os detalhes.</p>"
        ),
    })


def _order_event_payload(order: Order) -> dict:
    return {
        "order_id": order.id,
        "app_id": order.app_id,
        "module_name": order.module_name,
        "status": order.status,
        "amount": order.amount,
    }


def _record_status_event(order: Order, db: Session) -> None:
    """Registra o status atual do pedido na linha do tempo. Chamado na criação
    (status inicial) e em toda mudança de status feita pelo dono ou pelo
    cliente (cancelamento)."""
    db.add(OrderStatusEvent(order_id=order.id, status=order.status))


def _notify_owner_order_cancelled(app: App, order: Order, db: Session) -> None:
    owner = db.query(User).filter(User.id == app.user_id).first()
    if not owner:
        return
    enqueue_job(db, "email", {
        "to": owner.email,
        "subject": f"Pedido cancelado pelo cliente em {app.name}",
        "html_body": f"<p>O cliente cancelou o pedido #{order.id} ({order.module_name}) antes do preparo.</p>",
    })


def _credit_loyalty_points(app_id: int, order: Order, db: Session) -> None:
    """Credita pontos de fidelidade quando um pedido passa a completed, com
    base em pontos_por_real configurado no módulo cartao_fidelidade. Só se
    aplica a pedidos de clientes logados (end_user_id) e só uma vez por
    pedido — o caller garante que o status anterior não era completed."""
    if not order.end_user_id:
        return
    settings = _get_module_settings(app_id, "cartao_fidelidade", db)
    try:
        pontos_por_real = float(settings.get("pontos_por_real") or 0)
    except (TypeError, ValueError):
        return
    if pontos_por_real <= 0:
        return
    points_earned = int((order.amount or 0) * pontos_por_real)
    if points_earned <= 0:
        return

    account = (
        db.query(LoyaltyAccount)
        .filter(LoyaltyAccount.app_id == app_id, LoyaltyAccount.end_user_id == order.end_user_id)
        .first()
    )
    if account:
        account.points += points_earned
    else:
        db.add(LoyaltyAccount(app_id=app_id, end_user_id=order.end_user_id, points=points_earned))
    db.commit()


def _get_module_settings(app_id: int, module_name: str, db: Session) -> dict:
    row = (
        db.query(AppConfig)
        .join(Module, AppConfig.module_id == Module.id)
        .filter(AppConfig.app_id == app_id, Module.name == module_name)
        .first()
    )
    return row.settings if row and row.settings else {}


async def _start_gateway_checkout(
    gateway: str, settings: dict, valor: float, titulo: str, order_id: int, notification_url: str | None = None
) -> tuple[str | None, str | None]:
    """Abre uma cobrança na gateway pelo valor real do carrinho — diferente do
    fluxo de módulo de pagamento avulso (routes/payments.py), que usa um valor
    fixo configurado nas settings. Devolve (checkout_url, payment_reference).
    notification_url (quando suportado pela gateway) faz o pagamento confirmar
    sozinho via webhook, sem depender do cliente voltar e chamar /confirm-payment."""
    if gateway == "mercado_pago":
        access_token = settings.get("access_token")
        if not access_token:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Módulo não configurado: falta o access_token do Mercado Pago")
        result = await checkout_mercado_pago(valor, titulo, access_token, external_reference=str(order_id), notification_url=notification_url)
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
        result = await checkout_pagseguro(valor, titulo, token, notification_url=notification_url)
        return result.get("checkout_url"), result.get("gateway_order_id")
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Gateway de pagamento inválida")


def _mark_order_confirmed(order: Order, app: App, db: Session) -> None:
    """Marca o pedido como confirmed e avisa o cliente — usado tanto pelo
    confirm-payment manual (cliente volta do checkout) quanto pelos webhooks
    das gateways (confirmação automática, sem depender do cliente voltar)."""
    order.status = "confirmed"
    _record_status_event(order, db)
    db.commit()
    db.refresh(order)
    _notify_customer_status_change(app, order, db)
    dispatch_webhook_event(db, order.app_id, "order.status_changed", _order_event_payload(order))


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
    dispatch_webhook_event(db, app_id, "order.created", _order_event_payload(order))

    return order


@router.post("/modules/{module_name}/cart-checkout", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_cart_checkout(
    app_id: int,
    module_name: str,
    payload: CartCheckoutRequest,
    request: Request,
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
        coupon, discount_amount, reason = validate_coupon(
            app_id, coupon_code, subtotal, db, end_user_id=end_user.id if end_user else None
        )
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
        pickup_point=payload.pickup_point if payload.fulfillment_type == "pickup" else None,
        delivery_slot=payload.delivery_slot,
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

    if end_user:
        db.query(AbandonedCart).filter(
            AbandonedCart.app_id == app_id,
            AbandonedCart.end_user_id == end_user.id,
            AbandonedCart.module_name == module_name,
        ).delete(synchronize_session=False)
        db.commit()

    _notify_owner_new_order(app, order, db)
    dispatch_webhook_event(db, app_id, "order.created", _order_event_payload(order))

    checkout_url = None
    if payload.gateway:
        gateway_settings = _get_module_settings(app_id, payload.gateway, db)
        scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
        host = request.headers.get("x-forwarded-host", request.headers.get("host", request.url.netloc))
        notification_url = f"{scheme}://{host}/api/apps/{app_id}/webhooks/{payload.gateway}?order_id={order.id}"
        checkout_url, payment_reference = await _start_gateway_checkout(
            payload.gateway, gateway_settings, total, app.name, order.id, notification_url=notification_url
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
            _mark_order_confirmed(order, app, db)

    return order


@router.get("/orders", response_model=List[OrderResponse])
async def list_orders(
    app_id: int,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista todos os pedidos do app (todos os módulos). Só quem tem acesso ao app pode ver."""
    get_app_for_read(app_id, db, current_user)

    query = db.query(Order).filter(Order.app_id == app_id)
    if status_filter:
        query = query.filter(Order.status == status_filter)

    return query.order_by(Order.created_at.desc()).all()


def _notify_customer_status_change(app: App, order: Order, db: Session) -> None:
    """Avisa o cliente final (se logado) que o status do pedido mudou —
    e-mail + push dedicado, cada um enfileirado na fila de background (com
    retry próprio), nunca conta no limite mensal de push (é notificação
    individual, não campanha)."""
    if not order.end_user_id:
        return
    label = ORDER_STATUS_LABELS.get(order.status, order.status)
    end_user = db.query(AppUser).filter(AppUser.id == order.end_user_id).first()
    if end_user:
        enqueue_job(db, "email", {
            "to": end_user.email,
            "subject": f"Pedido atualizado: {label}",
            "html_body": f"<p>Seu pedido em <b>{app.name}</b> agora está: <b>{label}</b>.</p>",
        })
    enqueue_job(db, "push", {
        "app_id": app.id,
        "end_user_id": order.end_user_id,
        "title": f"Pedido {label}",
        "body": f"Seu pedido em {app.name} agora está {label.lower()}.",
    })


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
    app = get_app_for_write(app_id, db, current_user)

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
        _credit_loyalty_points(app_id, order, db)
        check_and_issue_purchase_coupons(db, app_id, order)
        _notify_customer_status_change(app, order, db)
        dispatch_webhook_event(db, app_id, "order.status_changed", _order_event_payload(order))

    return orders


@router.put("/orders/{order_id}", response_model=OrderResponse)
async def update_order(
    app_id: int,
    order_id: int,
    order_update: OrderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Atualiza o status de um pedido. Dono e editores podem alterar."""
    app = get_app_for_write(app_id, db, current_user)

    order = db.query(Order).filter(Order.id == order_id, Order.app_id == app_id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    old_status = order.status
    if order_update.status != order.status:
        order.status = order_update.status
        _record_status_event(order, db)
    db.commit()
    db.refresh(order)

    if order.status == "completed" and old_status != "completed":
        _credit_loyalty_points(app_id, order, db)
        check_and_issue_purchase_coupons(db, app_id, order)

    if order.status != old_status:
        log_owner_action(
            db, app.user_id, "update_order_status", f"order:{order.id}",
            app_id=app_id, details=f"status: {old_status} -> {order.status}",
        )

    _notify_customer_status_change(app, order, db)
    dispatch_webhook_event(db, app_id, "order.status_changed", _order_event_payload(order))
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


@router.get("/modules/{module_name}/unlocked-items", response_model=List[int])
async def list_unlocked_items(
    app_id: int,
    module_name: str,
    db: Session = Depends(get_db),
    end_user: AppUser = Depends(get_current_end_user),
):
    """IDs dos itens (ex: posts de conteúdo pago) que o cliente final já
    desbloqueou — pedido próprio com pagamento confirmado contendo o item."""
    rows = (
        db.query(OrderItem.module_item_id)
        .join(Order, Order.id == OrderItem.order_id)
        .filter(
            Order.app_id == app_id,
            Order.module_name == module_name,
            Order.end_user_id == end_user.id,
            Order.status.in_(["confirmed", "completed"]),
            OrderItem.module_item_id.isnot(None),
        )
        .distinct()
        .all()
    )
    return [row[0] for row in rows]


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
    dispatch_webhook_event(db, app_id, "order.status_changed", _order_event_payload(order))
    return order


@router.get("/orders/report", response_model=SalesReportResponse)
async def get_sales_report(
    app_id: int,
    days: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Receita (só pedidos completed), contagem por status e top-10 produtos —
    opcionalmente filtrado aos últimos `days` dias. Só quem tem acesso ao app pode ver."""
    get_app_for_read(app_id, db, current_user)

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


def _compute_financial_report(db: Session, app_id: int, days: Optional[int]) -> FinancialReportResponse:
    """Vai além do relatório de vendas: frete e desconto total, valor perdido
    em cancelamentos, e receita quebrada por forma de entrega e de pagamento."""
    query = db.query(Order).filter(Order.app_id == app_id)
    if days:
        query = query.filter(Order.created_at >= datetime.now(timezone.utc) - timedelta(days=days))
    orders = query.all()

    completed = [o for o in orders if o.status == "completed"]
    cancelled = [o for o in orders if o.status == "cancelled"]

    fulfillment_breakdown: dict = {}
    payment_breakdown: dict = {}
    for o in completed:
        f_key = o.fulfillment_type or "delivery"
        f_entry = fulfillment_breakdown.setdefault(f_key, {"count": 0, "revenue": 0.0})
        f_entry["count"] += 1
        f_entry["revenue"] += o.amount or 0

        p_key = o.payment_method or "pagamento_na_entrega"
        p_entry = payment_breakdown.setdefault(p_key, {"count": 0, "revenue": 0.0})
        p_entry["count"] += 1
        p_entry["revenue"] += o.amount or 0

    return FinancialReportResponse(
        total_revenue=sum(o.amount or 0 for o in completed),
        total_delivery_fees=sum(o.delivery_fee or 0 for o in completed),
        total_discounts=sum(o.discount_amount or 0 for o in completed),
        cancelled_count=len(cancelled),
        cancelled_value=sum(o.amount or 0 for o in cancelled),
        by_fulfillment_type=[
            FinancialBreakdownItem(key=k, count=v["count"], revenue=v["revenue"])
            for k, v in sorted(fulfillment_breakdown.items())
        ],
        by_payment_method=[
            FinancialBreakdownItem(key=k, count=v["count"], revenue=v["revenue"])
            for k, v in sorted(payment_breakdown.items())
        ],
    )


@router.get("/orders/financial-report", response_model=FinancialReportResponse)
async def get_financial_report(
    app_id: int,
    days: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Relatório financeiro mais completo que o de vendas -- só quem tem
    acesso ao app pode ver."""
    get_app_for_read(app_id, db, current_user)
    return _compute_financial_report(db, app_id, days)


@router.get("/orders/financial-export.csv")
async def export_financial_report_csv(
    app_id: int,
    days: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Exporta o relatório financeiro consolidado em CSV. Só quem tem
    acesso ao app pode exportar."""
    get_app_for_read(app_id, db, current_user)
    report = _compute_financial_report(db, app_id, days)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["metrica", "valor"])
    writer.writerow(["receita_total", report.total_revenue])
    writer.writerow(["frete_total", report.total_delivery_fees])
    writer.writerow(["desconto_total", report.total_discounts])
    writer.writerow(["pedidos_cancelados", report.cancelled_count])
    writer.writerow(["valor_cancelado", report.cancelled_value])
    writer.writerow([])
    writer.writerow(["forma_entrega", "pedidos", "receita"])
    for item in report.by_fulfillment_type:
        writer.writerow([item.key, item.count, item.revenue])
    writer.writerow([])
    writer.writerow(["forma_pagamento", "pedidos", "receita"])
    for item in report.by_payment_method:
        writer.writerow([item.key, item.count, item.revenue])
    buffer.seek(0)

    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=financeiro_app_{app_id}.csv"},
    )


@router.get("/orders/export.csv")
async def export_orders_csv(
    app_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Exporta todos os pedidos do app em CSV — um pedido por linha, com um
    resumo dos itens. Só quem tem acesso ao app pode exportar."""
    get_app_for_read(app_id, db, current_user)

    orders = db.query(Order).filter(Order.app_id == app_id).order_by(Order.created_at.desc()).all()

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        "id", "modulo", "status", "criado_em", "itens", "subtotal", "frete",
        "desconto", "total", "forma_entrega", "mesa", "ponto_retirada", "horario_selecionado",
        "cupom", "dados_cliente",
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
            o.pickup_point or "",
            o.delivery_slot or "",
            o.coupon_code or "",
            "; ".join(f"{k}: {v}" for k, v in (o.data or {}).items()),
        ])
    buffer.seek(0)

    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=pedidos_app_{app_id}.csv"},
    )


