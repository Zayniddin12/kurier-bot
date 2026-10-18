from typing import Literal
from pydantic import BaseModel, Field


class CustomerIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    phone: str = Field(min_length=5, max_length=30)


class AddressIn(BaseModel):
    text: str = Field(min_length=1, max_length=400)
    district: str = ""
    lat: float | None = Field(None, ge=-90, le=90)
    lng: float | None = Field(None, ge=-180, le=180)


class ItemIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    qty: int = Field(ge=1, le=1000)
    price: int = Field(ge=0)


class PaymentIn(BaseModel):
    method: Literal["Payme", "Click", "Karta", "Naqd"]
    status: Literal["paid", "pending"] = "paid"


class OrderIn(BaseModel):
    external_id: str = Field(min_length=1, max_length=100)
    customer: CustomerIn
    address: AddressIn
    items: list[ItemIn] = Field(min_length=1)
    payment: PaymentIn
    note: str | None = Field(None, max_length=500)
    delivery_fee: int | None = Field(None, ge=0)


class PaymentUpdateIn(BaseModel):
    status: Literal["paid", "failed"]


class CancelIn(BaseModel):
    reason: str = Field(default="Restoran bekor qildi", max_length=300)


class RestStatusIn(BaseModel):
    status: Literal["open", "paused"]
    reason: str = ""
