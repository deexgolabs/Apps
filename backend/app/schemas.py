from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional, List

# ===== USER SCHEMAS =====


class UserBase(BaseModel):
    email: EmailStr
    full_name: str


class UserCreate(UserBase):
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    password: Optional[str] = None


class UserResponse(UserBase):
    id: int
    plan: str
    is_active: bool
    is_verified: bool
    is_admin: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


# ===== ADMIN SCHEMAS =====


class AdminUserResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    plan: str
    is_active: bool
    is_admin: bool
    is_verified: bool
    created_at: datetime
    app_count: int

    class Config:
        from_attributes = True


class AdminUserUpdate(BaseModel):
    plan: Optional[str] = None
    is_admin: Optional[bool] = None
    is_active: Optional[bool] = None


class AdminAppResponse(BaseModel):
    id: int
    name: str
    status: str
    template_type: str
    owner_email: str
    created_at: datetime

    class Config:
        from_attributes = True


class AdminAppDetailResponse(AdminAppResponse):
    description: Optional[str] = None
    config: dict
    modules: list
    updated_at: datetime


class AdminAppStatusUpdate(BaseModel):
    status: str  # published | draft | suspended


class PlanConfigResponse(BaseModel):
    plan_name: str
    price: float
    max_apps: int
    max_modules: int
    max_items: int
    max_categories: int
    max_push_sends_per_month: int

    class Config:
        from_attributes = True


class PlanConfigUpdate(BaseModel):
    price: Optional[float] = None
    max_apps: Optional[int] = None
    max_modules: Optional[int] = None
    max_items: Optional[int] = None
    max_categories: Optional[int] = None
    max_push_sends_per_month: Optional[int] = None


class AdminAuditLogResponse(BaseModel):
    id: int
    admin_id: int
    admin_email: str
    action: str
    target: str
    details: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AdminStatsResponse(BaseModel):
    mrr: float
    published_apps: int
    total_apps: int
    users_by_plan: dict


# ===== BILLING SCHEMAS =====


class BillingCheckoutRequest(BaseModel):
    gateway: str  # mercado_pago | paypal | pagseguro
    plan: str  # pro | business


class BillingConfirmRequest(BaseModel):
    plan: str


# ===== PUSH NOTIFICATION SCHEMAS =====


class PushSubscriptionKeys(BaseModel):
    p256dh: str
    auth: str


class PushSubscriptionCreate(BaseModel):
    endpoint: str
    keys: PushSubscriptionKeys


class PushSendRequest(BaseModel):
    title: str
    body: str


class PushSendLogResponse(BaseModel):
    id: int
    title: Optional[str] = None
    body: Optional[str] = None
    sent_at: datetime

    class Config:
        from_attributes = True


# ===== APP SCHEMAS =====


class AppBase(BaseModel):
    name: str
    description: Optional[str] = None
    template_type: str


class AppCreate(AppBase):
    config: Optional[dict] = None


class AppUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    config: Optional[dict] = None
    modules: Optional[List[str]] = None
    status: Optional[str] = None


class AppResponse(AppBase):
    id: int
    user_id: int
    status: str
    config: dict
    modules: list
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ===== MODULE SCHEMAS =====


class ModuleResponse(BaseModel):
    id: int
    name: str
    description: str
    category: str
    icon_url: Optional[str] = None
    requires_plan: str
    features: list

    class Config:
        from_attributes = True


# ===== MODULE CONFIG SCHEMAS =====


class ModuleConfigUpdate(BaseModel):
    settings: dict


class ModuleConfigResponse(BaseModel):
    settings: dict


# ===== END USER (usuário final do app publicado) SCHEMAS =====


class EndUserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str


class EndUserLogin(BaseModel):
    email: EmailStr
    password: str


class EndUserResponse(BaseModel):
    id: int
    app_id: int
    email: EmailStr
    full_name: str
    phone: Optional[str] = None
    address: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class EndUserToken(BaseModel):
    access_token: str
    token_type: str
    user: EndUserResponse


class EndUserProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    current_password: Optional[str] = None
    new_password: Optional[str] = None


# ===== FORM SUBMISSION SCHEMAS =====


class SubmissionCreate(BaseModel):
    data: dict


class SubmissionResponse(BaseModel):
    id: int
    app_id: int
    module_name: str
    data: dict
    created_at: datetime

    class Config:
        from_attributes = True


# ===== ORDER SCHEMAS =====


class OrderCreate(BaseModel):
    data: dict
    amount: Optional[float] = None
    payment_method: Optional[str] = None
    payment_reference: Optional[str] = None


class OrderUpdate(BaseModel):
    status: str


class OrderItemResponse(BaseModel):
    id: int
    module_item_id: Optional[int] = None
    item_variation_id: Optional[int] = None
    name: str
    unit_price: float
    quantity: int
    subtotal: float

    class Config:
        from_attributes = True


class OrderStatusEventResponse(BaseModel):
    id: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class OrderResponse(BaseModel):
    id: int
    app_id: int
    module_name: str
    end_user_id: Optional[int] = None
    data: dict
    amount: Optional[float] = None
    subtotal: Optional[float] = None
    delivery_fee: Optional[float] = None
    discount_amount: Optional[float] = None
    coupon_code: Optional[str] = None
    fulfillment_type: Optional[str] = None
    table_number: Optional[str] = None
    payment_method: Optional[str] = None
    payment_reference: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime
    items: List[OrderItemResponse] = []
    status_events: List[OrderStatusEventResponse] = []
    checkout_url: Optional[str] = None

    class Config:
        from_attributes = True


class CartItemInput(BaseModel):
    item_id: int
    variation_id: Optional[int] = None
    variation_ids: List[int] = []
    quantity: int = 1


class CartCheckoutRequest(BaseModel):
    items: List[CartItemInput]
    customer: dict = {}
    coupon_code: Optional[str] = None
    fulfillment_type: str = "delivery"
    cep: Optional[str] = None
    gateway: Optional[str] = None
    table_number: Optional[str] = None


class SalesReportProduct(BaseModel):
    name: str
    quantity: int
    revenue: float


class SalesReportResponse(BaseModel):
    revenue: float
    orders_by_status: dict
    top_products: List[SalesReportProduct]


class CloseTableRequest(BaseModel):
    table_number: str


class CouponCreate(BaseModel):
    code: str
    discount_type: str = "percent"  # percent | fixed
    discount_value: float
    min_order_value: Optional[float] = None
    max_uses: Optional[int] = None
    active: bool = True
    expires_at: Optional[datetime] = None


class CouponUpdate(BaseModel):
    discount_type: Optional[str] = None
    discount_value: Optional[float] = None
    min_order_value: Optional[float] = None
    max_uses: Optional[int] = None
    active: Optional[bool] = None
    expires_at: Optional[datetime] = None


class CouponResponse(BaseModel):
    id: int
    app_id: int
    code: str
    discount_type: str
    discount_value: float
    min_order_value: Optional[float] = None
    max_uses: Optional[int] = None
    uses_count: int
    active: bool
    expires_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class CouponValidateRequest(BaseModel):
    code: str
    subtotal: float


class CouponValidateResponse(BaseModel):
    valid: bool
    discount_amount: float = 0
    reason: Optional[str] = None


# ===== CATEGORY / ITEM SCHEMAS =====


class CategoryCreate(BaseModel):
    name: str
    order: int = 0


class CategoryResponse(BaseModel):
    id: int
    app_id: int
    module_name: str
    name: str
    order: int

    class Config:
        from_attributes = True


class ItemCreate(BaseModel):
    name: str
    description: Optional[str] = None
    price: Optional[float] = None
    image_url: Optional[str] = None
    category_id: Optional[int] = None
    extra: dict = {}
    order: int = 0
    stock: Optional[int] = None


class ItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    image_url: Optional[str] = None
    category_id: Optional[int] = None
    extra: Optional[dict] = None
    order: Optional[int] = None
    stock: Optional[int] = None


class VariationCreate(BaseModel):
    name: str
    price: float
    stock: Optional[int] = None
    order: int = 0
    group_name: Optional[str] = None


class VariationUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None
    stock: Optional[int] = None
    order: Optional[int] = None
    group_name: Optional[str] = None


class VariationResponse(BaseModel):
    id: int
    item_id: int
    name: str
    price: float
    stock: Optional[int] = None
    order: int
    group_name: Optional[str] = None

    class Config:
        from_attributes = True


class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: Optional[str] = None


class ReviewResponse(BaseModel):
    id: int
    item_id: int
    end_user_id: int
    end_user_name: str
    rating: int
    comment: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ItemResponse(BaseModel):
    id: int
    app_id: int
    module_name: str
    category_id: Optional[int] = None
    name: str
    description: Optional[str] = None
    price: Optional[float] = None
    image_url: Optional[str] = None
    extra: dict
    order: int
    stock: Optional[int] = None
    variations: List[VariationResponse] = []
    avg_rating: Optional[float] = None
    review_count: int = 0

    class Config:
        from_attributes = True


# ===== AUTH RESPONSE =====


class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


class TokenData(BaseModel):
    email: Optional[str] = None
