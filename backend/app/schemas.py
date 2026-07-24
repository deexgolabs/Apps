from pydantic import BaseModel, EmailStr
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
    created_at: datetime

    class Config:
        from_attributes = True


class EndUserToken(BaseModel):
    access_token: str
    token_type: str
    user: EndUserResponse


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


class ItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    image_url: Optional[str] = None
    category_id: Optional[int] = None
    extra: Optional[dict] = None
    order: Optional[int] = None


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

    class Config:
        from_attributes = True


# ===== AUTH RESPONSE =====


class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


class TokenData(BaseModel):
    email: Optional[str] = None
