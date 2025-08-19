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
