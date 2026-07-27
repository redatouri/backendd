from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class CustomerIn(BaseModel):
    full_name: str = Field(min_length=2)
    phone: str = Field(min_length=8)
    email: str | None = None
    city: str = Field(min_length=2)
    neighborhood: str = Field(min_length=2)
    address_line: str = Field(min_length=5)
    locale: str = "fr"


class OrderItemIn(BaseModel):
    offer_id: UUID
    quantity: int = Field(ge=1, le=20)


class OrderCreateIn(BaseModel):
    customer: CustomerIn
    items: list[OrderItemIn] = Field(min_length=1)
    notes: str | None = None


class OrderItemOut(BaseModel):
    product_name: str
    offer_label: str
    unit_price: Decimal
    quantity: int
    line_total: Decimal


class OrderOut(BaseModel):
    id: UUID
    order_number: str
    status: str
    payment_method: str
    subtotal: Decimal
    shipping_fee: Decimal
    total: Decimal
    items: list[OrderItemOut]
    created_at: str


class OrderStatusPatchIn(BaseModel):
    status: str | None = None
    admin_notes: str | None = None
