from sqlalchemy import Column, Integer, String, DateTime, JSON, Boolean, ForeignKey, Float, UniqueConstraint
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime, timezone

Base = declarative_base()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    plan = Column(String, default="free")  # free, pro, business
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)


class App(Base):
    __tablename__ = "apps"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    template_type = Column(String, nullable=False)  # restaurant, store, service, etc
    config = Column(JSON, default=dict)  # cores, logo, textos
    modules = Column(JSON, default=list)  # módulos ativados (lista de nomes)
    status = Column(String, default="draft")  # draft, published
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Module(Base):
    __tablename__ = "modules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(String, nullable=False)
    category = Column(String, nullable=False)  # food, ordering, content, etc
    icon_url = Column(String, nullable=True)
    requires_plan = Column(String, default="free")  # free, pro, business
    features = Column(JSON, default=list)


class AppConfig(Base):
    __tablename__ = "app_configs"

    id = Column(Integer, primary_key=True, index=True)
    app_id = Column(Integer, ForeignKey("apps.id"), nullable=False)
    module_id = Column(Integer, ForeignKey("modules.id"), nullable=False)
    settings = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=utcnow)


class FormSubmission(Base):
    __tablename__ = "form_submissions"

    id = Column(Integer, primary_key=True, index=True)
    app_id = Column(Integer, ForeignKey("apps.id"), nullable=False)
    module_name = Column(String, nullable=False)
    data = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=utcnow)


class AppUser(Base):
    __tablename__ = "app_users"
    __table_args__ = (UniqueConstraint("app_id", "email", name="uq_app_users_app_id_email"),)

    id = Column(Integer, primary_key=True, index=True)
    app_id = Column(Integer, ForeignKey("apps.id"), nullable=False)
    email = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    password_hash = Column(String, nullable=True)  # nulo pra contas via login social
    auth_provider = Column(String, default="local")  # local | facebook
    facebook_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)


class ModuleCategory(Base):
    __tablename__ = "module_categories"

    id = Column(Integer, primary_key=True, index=True)
    app_id = Column(Integer, ForeignKey("apps.id"), nullable=False)
    module_name = Column(String, nullable=False)
    name = Column(String, nullable=False)
    order = Column(Integer, default=0)


class PushSubscription(Base):
    __tablename__ = "push_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    app_id = Column(Integer, ForeignKey("apps.id"), nullable=False)
    endpoint = Column(String, unique=True, nullable=False)
    p256dh = Column(String, nullable=False)
    auth = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)


class PushSendLog(Base):
    """Um registro por chamada de envio (broadcast), não por assinante —
    o limite do plano é sobre quantos envios o dono do app dispara por mês."""
    __tablename__ = "push_send_logs"

    id = Column(Integer, primary_key=True, index=True)
    app_id = Column(Integer, ForeignKey("apps.id"), nullable=False)
    title = Column(String, nullable=True)
    body = Column(String, nullable=True)
    sent_at = Column(DateTime(timezone=True), default=utcnow)


class Order(Base):
    """Pedido gerado por um módulo de formulário/pagamento (delivery, cotação,
    pagamento na entrega, checkout via gateway) — diferente de FormSubmission,
    que é só contato/avaliação sem workflow de status."""
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    app_id = Column(Integer, ForeignKey("apps.id"), nullable=False)
    module_name = Column(String, nullable=False)
    end_user_id = Column(Integer, ForeignKey("app_users.id"), nullable=True)
    data = Column(JSON, default=dict)
    amount = Column(Float, nullable=True)
    subtotal = Column(Float, nullable=True)  # soma dos OrderItem, antes de frete/desconto
    delivery_fee = Column(Float, nullable=True, default=0)
    discount_amount = Column(Float, nullable=True, default=0)
    coupon_code = Column(String, nullable=True)
    fulfillment_type = Column(String, nullable=True, default="delivery")  # delivery | pickup | dine_in
    payment_method = Column(String, nullable=True)
    payment_reference = Column(String, nullable=True)
    status = Column(String, default="pending")  # pending, confirmed, preparing, completed, cancelled
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    items = relationship("OrderItem", order_by="OrderItem.id", cascade="all, delete-orphan")


class OrderItem(Base):
    """Item estruturado de um pedido feito via carrinho (cardapio/catalogo).
    name/unit_price são snapshot no momento da compra — sobrevivem a mudanças
    ou remoção do ModuleItem original."""
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    module_item_id = Column(Integer, ForeignKey("module_items.id"), nullable=True)
    item_variation_id = Column(Integer, ForeignKey("item_variations.id"), nullable=True)
    name = Column(String, nullable=False)
    unit_price = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    subtotal = Column(Float, nullable=False)


class PlanConfig(Base):
    """Limites e preço de cada plano, editáveis pelo admin — substitui os
    valores fixos de PLAN_LIMITS/PLAN_PRICES (que continuam servindo de seed
    inicial e de fallback caso a linha do plano não exista por algum motivo)."""
    __tablename__ = "plan_configs"

    id = Column(Integer, primary_key=True, index=True)
    plan_name = Column(String, unique=True, index=True, nullable=False)
    price = Column(Float, default=0)
    max_apps = Column(Integer, default=1)
    max_modules = Column(Integer, default=5)
    max_items = Column(Integer, default=10)
    max_categories = Column(Integer, default=5)
    max_push_sends_per_month = Column(Integer, default=0)
    max_coupons = Column(Integer, default=0)


class Coupon(Base):
    __tablename__ = "coupons"
    __table_args__ = (UniqueConstraint("app_id", "code", name="uq_coupons_app_id_code"),)

    id = Column(Integer, primary_key=True, index=True)
    app_id = Column(Integer, ForeignKey("apps.id"), nullable=False)
    code = Column(String, nullable=False)  # sempre armazenado em maiúsculas
    discount_type = Column(String, nullable=False, default="percent")  # percent | fixed
    discount_value = Column(Float, nullable=False)
    min_order_value = Column(Float, nullable=True)
    max_uses = Column(Integer, nullable=True)
    uses_count = Column(Integer, nullable=False, default=0)
    active = Column(Boolean, default=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)


class AdminAuditLog(Base):
    __tablename__ = "admin_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String, nullable=False)
    target = Column(String, nullable=False)
    details = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)


class ModuleItem(Base):
    __tablename__ = "module_items"

    id = Column(Integer, primary_key=True, index=True)
    app_id = Column(Integer, ForeignKey("apps.id"), nullable=False)
    module_name = Column(String, nullable=False)
    category_id = Column(Integer, ForeignKey("module_categories.id"), nullable=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    price = Column(Float, nullable=True)
    image_url = Column(String, nullable=True)
    extra = Column(JSON, default=dict)
    order = Column(Integer, default=0)
    stock = Column(Integer, nullable=True)  # None = ilimitado/não rastreado

    variations = relationship("ItemVariation", order_by="ItemVariation.order")


class ItemVariation(Base):
    """Variação de um item (tamanho, sabor, cor) com preço absoluto próprio —
    quando um item tem variações, ModuleItem.price/stock viram só 'a partir de'
    e o checkout passa a exigir variation_id."""
    __tablename__ = "item_variations"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("module_items.id"), nullable=False)
    name = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    stock = Column(Integer, nullable=True)
    order = Column(Integer, default=0)


class ItemReview(Base):
    __tablename__ = "item_reviews"
    __table_args__ = (UniqueConstraint("item_id", "end_user_id", name="uq_item_reviews_item_end_user"),)

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("module_items.id"), nullable=False)
    end_user_id = Column(Integer, ForeignKey("app_users.id"), nullable=False)
    rating = Column(Integer, nullable=False)
    comment = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
