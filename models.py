from pydantic import BaseModel, EmailStr
from typing import List, Any


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    username: str
    email: EmailStr
    orders_count: int = 0
    total_spent: float = 0.0
    cart: List[Any] = []
    is_admin: bool = False


class LoginResponse(BaseModel):
    token: str
    user: UserOut


class AddToCartRequest(BaseModel):
    item_id: int
    qty: int


class CheckoutRequest(BaseModel):
    discount_code: str | None = None


class CartLineItem(BaseModel):
    item_id: int
    name: str
    price: float
    qty: int
    line_total: float


class CartView(BaseModel):
    items: List[CartLineItem]
    total: float


class OrderOut(BaseModel):
    id: str
    username: str
    items: List[Any]
    subtotal: float
    discount: float
    total: float
