from datetime import date
from pydantic import BaseModel, Field


class LoginIn(BaseModel):
    email: str
    password: str


class CancelIn(BaseModel):
    reason: str = Field(min_length=1, max_length=300)


class CourierIn(BaseModel):
    first_name: str = ""
    last_name: str = ""
    phone: str = ""
    pinfl: str = ""
    vehicle: str = "Skuter"
    shift: str = "09:00–21:00"
    birth_date: date | None = None
    license_no: str = ""
    vehicle_doc: str = ""
    plate: str = ""
    car_model: str = ""
    city: str = ""
    status: str = "active"


class CourierPatch(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    vehicle: str | None = None
    plate: str | None = None
    shift: str | None = None
    birth_date: date | None = None
    license_no: str | None = None
    vehicle_doc: str | None = None
    car_model: str | None = None
    city: str | None = None


class LedgerIn(BaseModel):
    type: str
    amount: int
    note: str | None = None


class RestaurantIn(BaseModel):
    name: str = Field(min_length=1)
    cuisine: str = ""
    district: str = ""
    address: str = ""
    lat: float
    lng: float
    integration_type: str = "API"
    pos_system: str = ""
    phone: str = ""
    webhook_url: str | None = None
    hours: str = "09:00–22:00"
    manager: str = ""
    color: str | None = None
    # restoran o'zida bor kalit bilan ulanishi mumkin; bo'sh bo'lsa platforma yangisini beradi
    api_key: str | None = Field(None, pattern=r"^yl_live_[A-Za-z0-9]{32}$")


class RestaurantPatch(BaseModel):
    name: str | None = None
    cuisine: str | None = None
    district: str | None = None
    address: str | None = None
    lat: float | None = None
    lng: float | None = None
    integration_type: str | None = None
    pos_system: str | None = None
    phone: str | None = None
    webhook_url: str | None = None
    hours: str | None = None
    manager: str | None = None
    prep_minutes: int | None = None
    color: str | None = None


class PauseIn(BaseModel):
    reason: str = ""


class OrderLocationIn(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    address: str | None = Field(default=None, max_length=400)


class AssignIn(BaseModel):
    courier_id: int


class OrderNotesIn(BaseModel):
    restaurant_note: str | None = Field(default=None, max_length=500)
    courier_note: str | None = Field(default=None, max_length=500)


class CustomerNoteIn(BaseModel):
    text: str = Field(min_length=1, max_length=500)


class BlockIn(BaseModel):
    reason: str = Field(default="", max_length=300)
