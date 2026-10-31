"""Telegram bot servisi uchun ichki API.

Bot kuryer nomidan harakat qilish uchun `/token` dan qisqa muddatli kuryer tokenini oladi va mavjud
`/api/courier/*` endpointlarini chaqiradi — shuning uchun biznes mantiq (taqsimlash, hisob-kitob) bitta joyda.
"""
import hmac
import re
import time
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_db
from app.errors import ApiError
from app.models import Courier, Order, OrderItem, OrderOffer, Restaurant
from app.security import create_token
from app.services.events import commit
from app.services.ledger import courier_earning
from app.services.serializers import courier_brief, iso, now_utc

TOKEN_MINUTES = 10
LINK_ATTEMPTS = 5          # bitta Telegram akkaunt uchun
LINK_WINDOW = 600          # sekund
_attempts: dict[int, deque] = defaultdict(deque)


async def bot_auth(x_bot_key: str | None = Header(None)):
    if not settings.BOT_API_KEY:
        raise ApiError(503, "Bot integratsiyasi sozlanmagan (BOT_API_KEY)")
    if not x_bot_key or not hmac.compare_digest(x_bot_key.encode(), settings.BOT_API_KEY.encode()):
        raise ApiError(401, "Bot kaliti noto'g'ri")


router = APIRouter(prefix="/api/bot", tags=["bot"], dependencies=[Depends(bot_auth)])


class LinkIn(BaseModel):
    telegram_id: int
    phone: str


class TokenIn(BaseModel):
    telegram_id: int


@router.post("/link")
async def link(body: LinkIn, db: AsyncSession = Depends(get_db)):
    """Kuryerni Telegram akkauntiga bog'lash: telefon admin panelda kiritilganiga mos bo'lishi shart (bot raqamni Telegram kontaktidan oladi)."""
    now = time.monotonic()
    q = _attempts[body.telegram_id]
    while q and now - q[0] > LINK_WINDOW:
        q.popleft()
    if len(q) >= LINK_ATTEMPTS:
        raise ApiError(429, "Juda ko'p urinish. 10 daqiqadan keyin qayta urinib ko'ring")
    q.append(now)

    ph = re.sub(r"\D", "", body.phone)[-9:]
    found = (await db.execute(select(Courier).where(Courier.phone == ph))).scalars().all() if len(ph) == 9 else []
    if not found:
        raise ApiError(401, "Bu raqam topilmadi. Kuryer admin panelda ro'yxatdan o'tgan bo'lishi kerak")
    if len(found) > 1:
        raise ApiError(409, "Bu raqam bilan bir nechta kuryer bor. Admin bilan bog'laning")
    c = found[0]
    if c.account_status != "active":
        raise ApiError(403, "Akkaunt bloklangan. Admin bilan bog'laning")
    # Telefon Telegram kontaktidan (bot user_id == from.id ni tekshiradi) kelgani uchun ishonchli:
    # kuryer akkauntini yo'qotib yangisidan kirsa, eski ulanish almashtiriladi.
    other = (await db.execute(select(Courier).where(Courier.telegram_id == body.telegram_id))).scalar_one_or_none()
    if other and other.id != c.id:
        raise ApiError(409, "Bu Telegram akkaunt boshqa kuryerga ulangan")
    c.telegram_id = body.telegram_id
    await commit(db)
    q.clear()
    return {"courier": courier_brief(c)}


@router.post("/token")
async def token(body: TokenIn, db: AsyncSession = Depends(get_db)):
    c = (await db.execute(select(Courier).where(Courier.telegram_id == body.telegram_id))).scalar_one_or_none()
    if not c:
        raise ApiError(404, "Ro'yxatdan o'tmagansiz")
    if c.account_status != "active":
        raise ApiError(403, "Akkaunt bloklangan. Admin bilan bog'laning")
    return {"access_token": create_token(str(c.id), "courier", TOKEN_MINUTES), "courier": courier_brief(c)}


def _order_payload(o: Order, r: Restaurant, items: list[OrderItem]) -> dict:
    return {
        "id": o.id, "external_id": o.external_id, "status": o.status,
        "restaurant": {"name": r.name, "address": r.address, "phone": r.phone, "lat": r.lat, "lng": r.lng},
        "customer": {"name": o.customer_name, "phone": o.customer_phone, "district": o.district,
                     "address": o.address, "lat": o.lat, "lng": o.lng},
        "items": [{"name": i.name, "qty": i.qty} for i in items],
        "subtotal": o.subtotal, "delivery_fee": o.delivery_fee, "total": o.total, "distance_km": o.distance_km,
        "pay_method": o.pay_method, "pay_status": o.pay_status, "collect_cash": o.pay_method == "Naqd",
        "note": o.note, "earning": courier_earning(o.delivery_fee),
    }


@router.get("/state")
async def state(telegram_id: int | None = None, db: AsyncSession = Depends(get_db)):
    """Bog'langan kuryerlarning joriy holati: kutayotgan taklif va joriy buyurtma. Bot shuni solishtirib xabar yuboradi."""
    qs = select(Courier).where(Courier.telegram_id.is_not(None), Courier.account_status == "active")
    if telegram_id is not None:
        qs = qs.where(Courier.telegram_id == telegram_id)
    couriers = (await db.execute(qs)).scalars().all()
    if not couriers:
        return {"couriers": []}
    ids = [c.id for c in couriers]
    now = now_utc()
    offers = {of.courier_id: of for of in (await db.execute(select(OrderOffer).where(
        OrderOffer.courier_id.in_(ids), OrderOffer.result == "pending", OrderOffer.expires_at > now))).scalars()}
    oids = {c.current_order_id for c in couriers if c.current_order_id} | {of.order_id for of in offers.values()}
    orders = {o.id: o for o in (await db.execute(select(Order).where(Order.id.in_(oids)))).scalars()} if oids else {}
    rests = {r.id: r for r in (await db.execute(select(Restaurant).where(
        Restaurant.id.in_({o.restaurant_id for o in orders.values()})))).scalars()} if orders else {}
    items: dict[int, list[OrderItem]] = defaultdict(list)
    if orders:
        for i in (await db.execute(select(OrderItem).where(OrderItem.order_id.in_(orders)).order_by(OrderItem.id))).scalars():
            items[i.order_id].append(i)

    out = []
    for c in couriers:
        of = offers.get(c.id)
        offer = None
        if of and of.order_id in orders:
            o = orders[of.order_id]
            r = rests[o.restaurant_id]
            offer = {"id": of.id, "order_id": o.id, "expires_at": iso(of.expires_at),
                     "restaurant": {"name": r.name, "address": r.address, "lat": r.lat, "lng": r.lng},
                     "customer": {"district": o.district, "address": o.address},
                     "distance_km": o.distance_km, "total": o.total, "pay_method": o.pay_method,
                     "collect_cash": o.pay_method == "Naqd", "earning": courier_earning(o.delivery_fee)}
        order = None
        o = orders.get(c.current_order_id) if c.current_order_id else None
        if o and o.courier_id == c.id and o.status in ("assigned", "onway"):
            order = _order_payload(o, rests[o.restaurant_id], items[o.id])
        out.append({"telegram_id": c.telegram_id, "courier_id": c.id, "name": f"{c.first_name} {c.last_name}",
                    "work_status": c.work_status, "balance": c.balance, "has_location": c.lat is not None,
                    "offer": offer, "order": order})
    return {"couriers": out}


@router.get("/orders/{oid}")
async def order_status(oid: int, db: AsyncSession = Depends(get_db)):
    """Joriy buyurtma yo'qolganda sababini aniqlash uchun (yetkazildi / bekor / boshqa kuryerga o'tdi)."""
    o = await db.get(Order, oid)
    if not o:
        raise ApiError(404, "Buyurtma topilmadi")
    return {"id": o.id, "status": o.status, "courier_id": o.courier_id, "cancel_reason": o.cancel_reason}
