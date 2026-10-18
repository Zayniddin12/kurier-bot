from datetime import timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import current_courier
from app.errors import ApiError
from app.models import Courier, Order, OrderOffer, Restaurant
from app.security import create_token
from app.services import dispatch
from app.services.events import commit, esc, feed
from app.services.ledger import courier_earning
from app.services.live import courier_changed
from app.services.orders import OrderError
from app.services.serializers import courier_brief, full_name, iso, now_utc

router = APIRouter(prefix="/api/courier", tags=["courier"])


class LoginIn(BaseModel):
    phone: str
    pinfl: str


class LocIn(BaseModel):
    lat: float
    lng: float


class IssueIn(BaseModel):
    kind: str


def wrap(fn):
    async def inner(*a, **k):
        try:
            return await fn(*a, **k)
        except OrderError as e:
            raise ApiError(e.status, e.message)
    inner.__name__ = fn.__name__
    return inner


@router.post("/login")
async def login(body: LoginIn, db: AsyncSession = Depends(get_db)):
    import re
    ph = re.sub(r"\D", "", body.phone)[-9:]
    c = (await db.execute(select(Courier).where(Courier.phone == ph, Courier.pinfl == body.pinfl))).scalar_one_or_none()
    if not c or c.account_status != "active":
        raise ApiError(401, "Telefon yoki JShShIR noto'g'ri")
    return {"access_token": create_token(str(c.id), "courier", 60 * 24 * 30), "courier": courier_brief(c)}


@router.post("/shift/start")
async def shift_start(c: Courier = Depends(current_courier), db: AsyncSession = Depends(get_db)):
    now = now_utc()
    if c.work_status == "offline":
        c.work_status, c.online_since, c.idle_since = "idle", now, now
    await courier_changed(db, c)
    await commit(db)
    return {"work_status": c.work_status}


@router.post("/shift/end")
async def shift_end(c: Courier = Depends(current_courier), db: AsyncSession = Depends(get_db)):
    if c.current_order_id:
        raise ApiError(409, "Faol buyurtma bor — avval yakunlang")
    c.work_status, c.online_since, c.idle_since = "offline", None, None
    await dispatch.expire_courier_offers(db, c)
    await courier_changed(db, c)
    await commit(db)
    return {"work_status": c.work_status}


@router.post("/break/start")
async def break_start(c: Courier = Depends(current_courier), db: AsyncSession = Depends(get_db)):
    if c.current_order_id or c.work_status != "idle":
        raise ApiError(409, "Tanaffusga faqat bo'sh paytda chiqish mumkin")
    c.work_status, c.break_until, c.idle_since = "break", now_utc() + timedelta(minutes=15), None
    await dispatch.expire_courier_offers(db, c)
    await courier_changed(db, c)
    await commit(db)
    return {"work_status": c.work_status, "break_until": iso(c.break_until)}


@router.post("/break/end")
async def break_end(c: Courier = Depends(current_courier), db: AsyncSession = Depends(get_db)):
    if c.work_status == "break":
        c.work_status, c.break_until, c.idle_since = "idle", None, now_utc()
        await feed(db, f"<b>{esc(full_name(c))} #{c.number}</b> tanaffusdan qaytdi", "amber")
        await courier_changed(db, c)
        await commit(db)
    return {"work_status": c.work_status}


@router.post("/location")
async def location(body: LocIn, c: Courier = Depends(current_courier), db: AsyncSession = Depends(get_db)):
    c.lat, c.lng, c.location_updated_at = body.lat, body.lng, now_utc()
    await courier_changed(db, c)
    await commit(db)
    return {"ok": True}


@router.get("/offers/current")
async def current_offer(c: Courier = Depends(current_courier), db: AsyncSession = Depends(get_db)):
    of = (await db.execute(select(OrderOffer).where(OrderOffer.courier_id == c.id, OrderOffer.result == "pending",
                                                    OrderOffer.expires_at > now_utc()))).scalars().first()
    if not of:
        return None
    o = await db.get(Order, of.order_id)
    r = await db.get(Restaurant, o.restaurant_id)
    return {"id": of.id, "order_id": o.id, "expires_at": iso(of.expires_at),
            "restaurant": {"name": r.name, "address": r.address, "lat": r.lat, "lng": r.lng},
            "customer": {"district": o.district, "address": o.address, "lat": o.lat, "lng": o.lng},
            "distance_km": o.distance_km, "total": o.total, "pay_method": o.pay_method,
            "collect_cash": o.pay_method == "Naqd", "earning": courier_earning(o.delivery_fee)}


async def _offer(db, c, oid):
    of = await db.get(OrderOffer, oid)
    if not of or of.courier_id != c.id:
        raise ApiError(404, "Taklif topilmadi")
    return of


@router.post("/offers/{oid}/accept")
async def accept(oid: int, c: Courier = Depends(current_courier), db: AsyncSession = Depends(get_db)):
    of = await _offer(db, c, oid)
    try:
        await dispatch.accept_offer(db, of, c)
    except OrderError as e:
        await commit(db)
        raise ApiError(e.status, e.message)
    await commit(db)
    return {"order_id": of.order_id}


@router.post("/offers/{oid}/decline")
async def decline(oid: int, c: Courier = Depends(current_courier), db: AsyncSession = Depends(get_db)):
    of = await _offer(db, c, oid)
    try:
        await dispatch.decline_offer(db, of, c)
    except OrderError as e:
        raise ApiError(e.status, e.message)
    await commit(db)
    return {"ok": True}


async def _order(db, c, oid) -> Order:
    o = await db.get(Order, oid)
    if not o or o.courier_id != c.id:
        raise ApiError(404, "Buyurtma topilmadi")
    return o


@router.post("/orders/{oid}/picked-up")
async def picked(oid: int, c: Courier = Depends(current_courier), db: AsyncSession = Depends(get_db)):
    o = await _order(db, c, oid)
    try:
        await dispatch.picked_up(db, o, c)
    except OrderError as e:
        raise ApiError(e.status, e.message)
    await commit(db)
    return {"status": o.status}


@router.post("/orders/{oid}/delivered")
async def delivered(oid: int, c: Courier = Depends(current_courier), db: AsyncSession = Depends(get_db)):
    o = await _order(db, c, oid)
    try:
        await dispatch.delivered(db, o, c)
    except OrderError as e:
        raise ApiError(e.status, e.message)
    await commit(db)
    return {"status": o.status, "balance": c.balance}


@router.post("/orders/{oid}/issue")
async def issue(oid: int, body: IssueIn, c: Courier = Depends(current_courier), db: AsyncSession = Depends(get_db)):
    o = await _order(db, c, oid)
    if c.current_order_id != o.id:
        raise ApiError(409, "Bu joriy buyurtma emas")
    try:
        i = await dispatch.open_issue(db, c, body.kind)
    except OrderError as e:
        raise ApiError(e.status, e.message)
    await commit(db)
    return {"id": i.id, "kind": i.kind}
