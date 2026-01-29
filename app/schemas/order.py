
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, conint
from typing import Any, Literal


from app.schemas.user import UserOut


class OrderItemIn(BaseModel):
    product_id: str
    quantity: conint(ge=1) = 1


class OrderCreate(BaseModel):
    payment_method: str
    shipping_address: str
    phone: str
    notes: str | None = None
    location: dict[str, Any] | None = None
    items: list[OrderItemIn]


class OrderStatusUpdate(BaseModel):
    status: Literal["pending", "completed", "delivered"]


class OrderProductOut(BaseModel):
    product_id: str
    price: int
    quantity: int
    total_price: int
    name: str
    image: str | None
    weight: str | None
    description: str | None


class OrderOut(BaseModel):
    id: int
    total_price: int
    status: str
    payment_method: str
    shipping_address: str
    notes: str | None
    phone: str
    created_at: datetime
    delivery_date: datetime | None
    location: dict | None
    user: UserOut | None = None
    products: list[OrderProductOut]


class OrderProductOutDash(BaseModel):
    id: int
    order_id: int
    product_id: UUID  

    name: str
    image: str | None = None
    description: str | None = None
    weight: str | None = None

    price: float
    quantity: int
    total_price: float

    class Config:
        from_attributes = True