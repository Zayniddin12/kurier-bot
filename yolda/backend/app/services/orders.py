"""Buyurtma yaratish, to'lov va bekor qilish."""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models import Courier, Order, OrderIssue, OrderItem, OrderOffer, Restaurant
from app.services import webhooks
from app.services.events import emit, esc, feed
from app.services.geo import road_km
from app.services.ledger import delivery_fee_for
from app.services.serializers import now_utc, order_row


class OrderError(Exception):
    def __init__(self, message: str, status: int = 409):
        self.message, self.status = message, status


async def order_changed(db, o: Order, restaurant: Restaurant | None = None, event: str = "order.updated",
                        status_changed: bool = False):
    r = restaurant or await db.get(Restaurant, o.restaurant_id)
    c = await db.get(Courier, o.courier_id) if o.courier_id else None
    emit(db, event, order_row(o, r, c), r.id)
    emit(db, "alerts.changed", {}, r.id)
    if status_changed:
        webhooks.queue(db, o, r, c)


async def create_order(db, restaurant: Restaurant, *, external_id: str, customer_name: str, customer_phone: str,
                       address: str, district: str = "", lat=None, lng=None, items: list[dict],
                       pay_method: str, pay_status: str = "paid", note: str | None = None,
                       delivery_fee: int | None = None) -> tuple[Order, bool]:
    ex = (await db.execute(select(Order).where(Order.restaurant_id == restaurant.id,
                                               Order.external_id == external_id))).scalar_one_or_none()
    if ex:
        return ex, False
    if restaurant.status == "paused":
        raise OrderError("Restoran hozir buyurtma qabul qilmayapti", 409)
    if not items:
        raise OrderError("Buyurtma tarkibi bo'sh", 422)
    km = None
    if lat is not None and lng is not None:
        km = road_km(restaurant.lat, restaurant.lng, lat, lng)
        fee = delivery_fee_for(km)
    elif delivery_fee is not None:
        fee = int(delivery_fee)
    else:
        raise OrderError("Koordinatalar yo'q bo'lsa delivery_fee majburiy", 422)
    subtotal = sum(int(i["qty"]) * int(i["price"]) for i in items)
    if pay_method == "Naqd":
        ps = "cod"
    else:
        ps = pay_status if pay_status in ("paid", "pending") else "paid"
    now = now_utc()
    o = Order(restaurant_id=restaurant.id, external_id=external_id, created_at=now, status="new", subtotal=subtotal,
              delivery_fee=fee, total=subtotal + fee, distance_km=km, pay_method=pay_method, pay_status=ps,
              customer_name=customer_name, customer_phone=customer_phone, district=district, address=address,
              lat=lat, lng=lng, note=note, declined_courier_ids=[], queued=False,
              search_started_at=None if ps == "pending" else now, prep_minutes=restaurant.prep_minutes)
    db.add(o)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        ex = (await db.execute(select(Order).where(Order.restaurant_id == restaurant.id,
                                                   Order.external_id == external_id))).scalar_one()
        return ex, False
    for i in items:
        db.add(OrderItem(order_id=o.id, name=i["name"], qty=int(i["qty"]), price=int(i["price"])))
    await feed(db, f"Yangi buyurtma <b>#{o.id}</b> · {esc(restaurant.name)} · {o.total:,} so'm".replace(",", " "),
               "brand", restaurant.id)
    await order_changed(db, o, restaurant, "order.created")
    return o, True


async def _release_courier(db, o: Order):
    from app.services.dispatch import finish_current
    if not o.courier_id:
        return
    c = await db.get(Courier, o.courier_id)
    if c and c.current_order_id == o.id:
        await finish_current(db, c)
    elif c:
        from app.services.live import courier_changed
        await courier_changed(db, c)


async def cancel_order(db, o: Order, reason: str, *, failed_payment: bool = False) -> bool:
    """Qaytaradi: to'lov mijozga qaytarildimi."""
    if o.status in ("delivered", "cancelled"):
        raise OrderError("Buyurtma allaqachon yakunlangan", 409)
    now = now_utc()
    refunded = False
    if failed_payment:
        o.pay_status = "failed"
    elif o.pay_status == "paid":
        o.pay_status, refunded = "refunded", True
    elif o.pay_status in ("cod", "pending"):
        o.pay_status = "void"
    for i in (await db.execute(select(OrderIssue).where(OrderIssue.order_id == o.id,
                                                        OrderIssue.ended_at.is_(None)))).scalars():
        i.ended_at, i.resolved_by = now, "buyurtma bekor qilindi"
        emit(db, "issue.closed", {"order_id": o.id, "issue_id": i.id}, o.restaurant_id)
    for of in (await db.execute(select(OrderOffer).where(OrderOffer.order_id == o.id,
                                                         OrderOffer.result == "pending"))).scalars():
        of.result = "expired"
    o.status, o.cancelled_at, o.cancel_reason = "cancelled", now, reason
    await _release_courier(db, o)
    o.queued, o.queue_position = False, None
    r = await db.get(Restaurant, o.restaurant_id)
    await feed(db, f"Bekor qilindi: <b>#{o.id}</b> · {esc(reason)}" + (" · to'lov qaytarildi" if refunded else ""),
               "red", r.id)
    await order_changed(db, o, r, status_changed=True)
    return refunded


async def set_payment(db, o: Order, status: str):
    if o.pay_status != "pending":
        raise OrderError("To'lov holati 'pending' emas", 409)
    if status == "paid":
        o.pay_status = "paid"
        o.search_started_at = now_utc()
        await feed(db, f"To'lov tasdiqlandi: <b>#{o.id}</b> · {o.pay_method}", "teal", o.restaurant_id)
        await order_changed(db, o)
    else:
        await cancel_order(db, o, "Onlayn to'lov o'tmadi", failed_payment=True)
