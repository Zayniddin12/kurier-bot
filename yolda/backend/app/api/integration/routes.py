import time
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, Query
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import ORDER_STATUS, TRANSPORTS, settings
from app.db import get_db
from app.deps import bearer
from app.errors import ApiError
from app.models import Courier, Order, Restaurant
from app.schemas.integration import CancelIn, OrderIn, PayIn, PaymentUpdateIn, RestStatusIn
from app.security import hash_key
from app.services import orders as osvc
from app.services import payments as psvc
from app.services.eta import compute_eta
from app.services.events import commit, emit, esc, feed
from app.services.geo import road_km
from app.services.ledger import delivery_fee_for
from app.services.serializers import iso, now_utc, restaurant_row

router = APIRouter(prefix="/api/v1", tags=["integration"])
_hits: dict[int, deque] = defaultdict(deque)


async def restaurant_auth(cred: HTTPAuthorizationCredentials | None = Depends(bearer),
                          db: AsyncSession = Depends(get_db)) -> Restaurant:
    if not cred:
        raise ApiError(401, "API kalit ko'rsatilmagan (Authorization: Bearer <api_key>)")
    r = (await db.execute(select(Restaurant).where(Restaurant.api_key_hash == hash_key(cred.credentials)))).scalar_one_or_none()
    if not r:
        raise ApiError(401, "API kalit noto'g'ri")
    now = time.monotonic()
    q = _hits[r.id]
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= settings.RATE_LIMIT_PER_MIN:
        raise ApiError(429, f"So'rovlar limiti oshdi ({settings.RATE_LIMIT_PER_MIN} so'rov/daqiqa)")
    q.append(now)
    r.last_sync_at = now_utc()
    await db.commit()
    return r


def short(o: Order) -> dict:
    return {"id": o.id, "external_id": o.external_id, "status": o.status, "status_text": ORDER_STATUS[o.status][0],
            "delivery_fee": o.delivery_fee, "total": o.total, "subtotal": o.subtotal, "distance_km": o.distance_km,
            "pay_status": o.pay_status}


async def find(db, r: Restaurant, ext: str) -> Order:
    o = (await db.execute(select(Order).where(Order.restaurant_id == r.id, Order.external_id == ext))).scalar_one_or_none()
    if not o:
        raise ApiError(404, "Buyurtma topilmadi")
    return o


@router.post("/orders", status_code=201)
async def create_order(body: OrderIn, r: Restaurant = Depends(restaurant_auth), db: AsyncSession = Depends(get_db)):
    from fastapi.responses import JSONResponse
    try:
        o, created = await osvc.create_order(
            db, r, external_id=body.external_id, customer_name=body.customer.name, customer_phone=body.customer.phone,
            address=body.address.text, district=body.address.district, lat=body.address.lat, lng=body.address.lng,
            items=[i.model_dump() for i in body.items], pay_method=body.payment.method,
            pay_status="pending" if body.payment.method == "Multicard" else body.payment.status, note=body.note, delivery_fee=body.delivery_fee)
    except osvc.OrderError as e:
        raise ApiError(e.status, e.message, "delivery_fee" if "delivery_fee" in e.message else None)
    await commit(db)
    d = short(o)
    if o.pay_method == "Multicard" and o.pay_status == "pending":
        try:   # buyurtma yaratildi; havola olinmasa restoran /pay ni qayta chaqiradi
            p = await psvc.create_payment(db, o, method=body.payment.system or "card")
            await commit(db)
            d["payment"] = psvc.payment_dict(p)
        except psvc.PaymentError as e:
            await db.rollback()
            d["payment"] = None
            d["payment_error"] = e.message
    return JSONResponse(d, status_code=201 if created else 200)


@router.get("/orders/{external_id}")
async def get_order(external_id: str, r: Restaurant = Depends(restaurant_auth), db: AsyncSession = Depends(get_db)):
    o = await find(db, r, external_id)
    c = await db.get(Courier, o.courier_id) if o.courier_id else None
    eta = compute_eta(o, c, r) if c and not o.queued else None
    d = short(o)
    d.update({"courier": {"name": f"{c.first_name} {c.last_name}", "phone": c.phone} if c else None,
              "eta_min": eta["eta_min"] if eta else None, "cancel_reason": o.cancel_reason,
              "times": {"created_at": iso(o.created_at), "assigned_at": iso(o.assigned_at), "picked_at": iso(o.picked_at),
                        "delivered_at": iso(o.delivered_at), "cancelled_at": iso(o.cancelled_at)}})
    return d


@router.post("/orders/{external_id}/payment")
async def payment(external_id: str, body: PaymentUpdateIn, r: Restaurant = Depends(restaurant_auth),
                  db: AsyncSession = Depends(get_db)):
    o = await find(db, r, external_id)
    try:
        await osvc.set_payment(db, o, body.status)
    except osvc.OrderError as e:
        raise ApiError(e.status, e.message)
    await commit(db)
    return short(o)


@router.get("/payment-methods")
async def payment_methods(r: Restaurant = Depends(restaurant_auth)):
    """Saytda mijozga ko'rsatiladigan onlayn to'lov usullari. `code` ni /pay (yoki POST /orders da payment.system) ga yuboring."""
    return {"methods": psvc.enabled_methods()}


@router.post("/orders/{external_id}/pay")
async def pay(external_id: str, body: PayIn | None = None, r: Restaurant = Depends(restaurant_auth),
              db: AsyncSession = Depends(get_db)):
    """Mijoz uchun onlayn to'lov havolasini yaratadi (Multicard). Idempotent. To'lov tushgach buyurtma avtomatik 'paid' bo'ladi."""
    o = await find(db, r, external_id)
    b = body or PayIn()
    try:
        p = await psvc.create_payment(db, o, method=b.method, return_url=b.return_url, return_error_url=b.return_error_url, lang=b.lang)
    except psvc.PaymentError as e:
        await db.rollback()
        raise ApiError(e.status, e.message)
    await commit(db)
    return {**short(o), "payment": psvc.payment_dict(p)}


@router.get("/orders/{external_id}/payment")
async def payment_status(external_id: str, r: Restaurant = Depends(restaurant_auth), db: AsyncSession = Depends(get_db)):
    from app.models import Payment
    o = await find(db, r, external_id)
    p = (await db.execute(select(Payment).where(Payment.order_id == o.id).order_by(Payment.id.desc()))).scalars().first()
    return {"pay_status": o.pay_status, "pay_method": o.pay_method, "payment": psvc.payment_dict(p) if p else None}


@router.post("/orders/{external_id}/cancel")
async def cancel(external_id: str, body: CancelIn | None = None, r: Restaurant = Depends(restaurant_auth),
                 db: AsyncSession = Depends(get_db)):
    o = await find(db, r, external_id)
    if o.status not in ("new", "assigned"):
        raise ApiError(409, "Buyurtmani endi bekor qilib bo'lmaydi")
    if o.status == "assigned" and o.picked_at:
        raise ApiError(409, "Buyurtmani endi bekor qilib bo'lmaydi")
    try:
        await osvc.cancel_order(db, o, (body.reason if body else None) or "Restoran bekor qildi")
    except osvc.OrderError as e:
        raise ApiError(e.status, e.message)
    await commit(db)
    return short(o)


@router.get("/quote")
async def quote(lat: float = Query(ge=-90, le=90), lng: float = Query(ge=-180, le=180),
                r: Restaurant = Depends(restaurant_auth)):
    km = road_km(r.lat, r.lng, lat, lng)
    eta = r.prep_minutes + round(km / TRANSPORTS["Skuter"]["speed"] * 60) + 5
    return {"distance_km": km, "delivery_fee": delivery_fee_for(km), "eta_min": eta}


@router.post("/restaurant/status")
async def rest_status(body: RestStatusIn, r: Restaurant = Depends(restaurant_auth), db: AsyncSession = Depends(get_db)):
    r = await db.merge(r)
    if body.status == "paused":
        r.status, r.pause_reason = "paused", body.reason or None
        await feed(db, f"<b>{esc(r.name)}</b> buyurtma qabul qilishni to'xtatdi", "amber", r.id)
    else:
        r.status, r.pause_reason = "open", None
        await feed(db, f"<b>{esc(r.name)}</b> qayta buyurtma qabul qilmoqda", "teal", r.id)
    emit(db, "restaurant.updated", restaurant_row(r), r.id)
    emit(db, "alerts.changed", {}, None)
    await commit(db)
    return {"status": r.status, "reason": r.pause_reason}
