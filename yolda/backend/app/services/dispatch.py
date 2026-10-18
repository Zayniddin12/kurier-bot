"""Avtomatik taqsimlash, kuryer holat o'tishlari va muammolar."""
from datetime import timedelta

from sqlalchemy import func, select

from app.config import ISSUES, SLA, TRANSPORTS, settings
from app.models import Courier, Order, OrderIssue, OrderOffer, Restaurant
from app.services import ledger
from app.services.events import emit, esc, feed
from app.services.geo import haversine
from app.services.live import courier_changed
from app.services.orders import OrderError, order_changed
from app.services.serializers import full_name, now_utc

OFFER_TTL = 30
QUEUE_AFTER = 60
RESTART_AFTER = 120
VEHICLE_AUTO = 60
QUEUE_PENALTY_KM = 5


def can_take(c, order, has_open_issue: bool) -> bool:
    if c.account_status != "active" or c.work_status in ("offline", "break") or has_open_issue:
        return False
    mx = TRANSPORTS.get(c.vehicle, {}).get("max_km")
    if mx is not None and order.distance_km is not None and order.distance_km > mx:
        return False
    if order.pay_method == "Naqd" and c.balance < -settings.CASH_LIMIT:
        return False
    return c.lat is not None


def candidate_distance(c, rest, current_customer: tuple | None, queue_len: int) -> float:
    if c.current_order_id is None:
        return haversine(c.lat, c.lng, rest.lat, rest.lng)
    if current_customer and current_customer[0] is not None:
        return (haversine(c.lat, c.lng, *current_customer) + haversine(*current_customer, rest.lat, rest.lng)
                + QUEUE_PENALTY_KM * queue_len)
    return haversine(c.lat, c.lng, rest.lat, rest.lng) + QUEUE_PENALTY_KM * queue_len


def _label(c) -> str:
    return f"<b>{esc(full_name(c))} #{c.number}</b>"


async def assign_to_courier(db, o: Order, c: Courier):
    now = now_utc()
    r = await db.get(Restaurant, o.restaurant_id)
    o.status, o.courier_id, o.assigned_at, o.queued, o.queue_position = "assigned", c.id, now, False, None
    o.prep_minutes = r.prep_minutes
    o.ready_at = o.created_at + timedelta(minutes=r.prep_minutes)
    c.current_order_id, c.work_status, c.idle_since = o.id, "pickup", None
    await feed(db, f"Tizim {_label(c)} ni <b>#{o.id}</b> buyurtmaga biriktirdi", "blue", r.id)
    await order_changed(db, o, r, status_changed=True)
    await courier_changed(db, c)


async def queue_to_courier(db, o: Order, c: Courier, pos: int):
    r = await db.get(Restaurant, o.restaurant_id)
    o.status, o.courier_id, o.assigned_at, o.queued, o.queue_position = "assigned", c.id, now_utc(), True, pos
    o.prep_minutes = r.prep_minutes
    await feed(db, f"Tizim <b>#{o.id}</b> ni {_label(c)} navbatiga qo'ydi", "blue", r.id)
    await order_changed(db, o, r, status_changed=True)
    await courier_changed(db, c)


async def finish_current(db, c: Courier):
    """Joriy buyurtma tugadi/bekor bo'ldi: navbatdagisini olish yoki bo'sh qolish."""
    nxt = (await db.execute(select(Order).where(Order.courier_id == c.id, Order.queued.is_(True),
                                                Order.status == "assigned")
                            .order_by(Order.queue_position, Order.assigned_at).limit(1))).scalar_one_or_none()
    c.current_order_id = None
    if nxt and c.account_status == "active" and c.work_status != "offline":
        nxt.queued, nxt.queue_position = False, None
        c.current_order_id, c.work_status, c.idle_since = nxt.id, "pickup", None
        await order_changed(db, nxt)
    elif c.work_status in ("delivering", "pickup"):
        c.work_status, c.idle_since = "idle", now_utc()
    await courier_changed(db, c)


async def accept_offer(db, offer: OrderOffer, c: Courier):
    now = now_utc()
    if offer.result != "pending" or offer.courier_id != c.id:
        raise OrderError("Taklif topilmadi yoki muddati o'tgan", 409)
    if offer.expires_at <= now:
        raise OrderError("Taklif muddati tugagan", 409)
    o = await db.get(Order, offer.order_id)
    if o.status != "new" or c.current_order_id is not None:
        offer.result = "expired"
        raise OrderError("Buyurtma endi mavjud emas", 409)
    offer.result = "accepted"
    await assign_to_courier(db, o, c)


async def decline_offer(db, offer: OrderOffer, c: Courier, expired: bool = False):
    if offer.result != "pending" or offer.courier_id != c.id:
        raise OrderError("Taklif topilmadi", 409)
    offer.result = "expired" if expired else "declined"
    o = await db.get(Order, offer.order_id)
    o.declined_courier_ids = list(o.declined_courier_ids or []) + [c.id]
    await feed(db, f"{_label(c)} <b>#{o.id}</b> ni rad etdi" + (" (vaqt tugadi)" if expired else ""),
               "amber", o.restaurant_id)
    await order_changed(db, o)


async def _pickup_point(db, o: Order, rest: Restaurant):
    return (o.handoff_lat, o.handoff_lng) if o.handoff_lat is not None else (rest.lat, rest.lng)


async def picked_up(db, o: Order, c: Courier):
    if o.courier_id != c.id or o.status != "assigned" or o.queued:
        raise OrderError("Buyurtmani olib ketib bo'lmaydi", 409)
    o.status, o.picked_at = "onway", now_utc()
    c.work_status = "delivering"
    await feed(db, f"{_label(c)} <b>#{o.id}</b> ni olib ketdi", "teal", o.restaurant_id)
    await order_changed(db, o, status_changed=True)
    await courier_changed(db, c)


async def delivered(db, o: Order, c: Courier):
    if o.courier_id != c.id or o.status != "onway":
        raise OrderError("Buyurtmani yetkazib bo'lmaydi", 409)
    now = now_utc()
    o.status, o.delivered_at = "delivered", now
    o.delivery_minutes = round((now - o.created_at).total_seconds() / 60) + (o.delay_added_minutes or 0)
    o.is_late = o.delivery_minutes > SLA
    await ledger.add_entry(db, c, "earn", ledger.courier_earning(o.delivery_fee), o.id, "Yetkazish haqi")
    if o.pay_method == "Naqd":
        o.pay_status = "collected"
        await ledger.add_entry(db, c, "cash", -o.total, o.id, "Naqd pul mijozdan olindi")
    await feed(db, f"Yetkazildi: <b>#{o.id}</b> · {esc(o.customer_name)}", "grey", o.restaurant_id)
    await order_changed(db, o, status_changed=True)
    await finish_current(db, c)


# ---------- Muammolar ----------
async def open_issue(db, c: Courier, kind: str) -> OrderIssue:
    if kind not in ISSUES:
        raise OrderError("Noma'lum muammo turi", 422)
    if not c.current_order_id:
        raise OrderError("Kuryerda faol buyurtma yo'q", 409)
    meta = ISSUES[kind]
    if meta["when"] == "delivering" and c.work_status != "delivering":
        raise OrderError("Bu muammo faqat mijozga yo'lda bo'lganda yuboriladi", 409)
    if meta["when"] == "pickup" and c.work_status != "pickup":
        raise OrderError("Bu muammo faqat restoranga yo'lda bo'lganda yuboriladi", 409)
    ex = (await db.execute(select(OrderIssue).where(OrderIssue.order_id == c.current_order_id,
                                                    OrderIssue.ended_at.is_(None)))).scalar_one_or_none()
    if ex:
        raise OrderError("Ochiq muammo allaqachon bor", 409)
    now = now_utc()
    o = await db.get(Order, c.current_order_id)
    i = OrderIssue(order_id=o.id, courier_id=c.id, kind=kind, started_at=now,
                   auto_at=now + timedelta(seconds=VEHICLE_AUTO) if kind == "vehicle" else None)
    db.add(i)
    await db.flush()
    await feed(db, f"Muammo: <b>#{o.id}</b> · {meta['text']}", "red", o.restaurant_id)
    emit(db, "issue.opened", {"id": i.id, "order_id": o.id, "courier_id": c.id, "kind": kind, "text": meta["text"]},
         o.restaurant_id)
    await order_changed(db, o)
    await courier_changed(db, c)
    return i


async def open_issue_for_order(db, o: Order):
    return (await db.execute(select(OrderIssue).where(OrderIssue.order_id == o.id,
                                                      OrderIssue.ended_at.is_(None)))).scalars().first()


async def resolve_issue(db, o: Order, by: str = "operator") -> OrderIssue:
    i = await open_issue_for_order(db, o)
    if not i:
        raise OrderError("Ochiq muammo yo'q", 409)
    i.ended_at, i.resolved_by = now_utc(), by
    o.delay_added_minutes = (o.delay_added_minutes or 0) + ISSUES[i.kind]["delay"]
    await feed(db, f"Hal qilindi: <b>#{o.id}</b> · {ISSUES[i.kind]['text']}", "teal", o.restaurant_id)
    emit(db, "issue.closed", {"id": i.id, "order_id": o.id, "courier_id": i.courier_id}, o.restaurant_id)
    await order_changed(db, o)
    if o.courier_id:
        await courier_changed(db, await db.get(Courier, o.courier_id))
    return i


async def reassign_order(db, o: Order, by: str = "operator"):
    if o.status not in ("assigned", "onway") or not o.courier_id:
        raise OrderError("Buyurtmani o'tkazib bo'lmaydi", 409)
    now = now_utc()
    c = await db.get(Courier, o.courier_id)
    i = await open_issue_for_order(db, o)
    if i:
        i.ended_at, i.resolved_by = now, by
        emit(db, "issue.closed", {"id": i.id, "order_id": o.id, "courier_id": c.id}, o.restaurant_id)
    if o.status == "onway" and c.lat is not None:
        o.handoff_lat, o.handoff_lng = c.lat, c.lng
        o.handoff_name = f"Kuryer #{c.number} qolgan joy"
    queued = (await db.execute(select(Order).where(Order.courier_id == c.id, Order.queued.is_(True),
                                                   Order.status == "assigned"))).scalars().all()
    for q in queued:
        q.status, q.courier_id, q.queued, q.queue_position = "new", None, False, None
        q.search_started_at = now
        await order_changed(db, q)
    o.status, o.courier_id, o.queued, o.queue_position = "new", None, False, None
    o.declined_courier_ids = [c.id]
    o.reassigned_count = (o.reassigned_count or 0) + 1
    o.search_started_at, o.assigned_at, o.picked_at = now, None, None
    c.work_status, c.current_order_id, c.idle_since = "offline", None, None
    await feed(db, f"<b>#{o.id}</b> {_label(c)} dan boshqa kuryerga o'tkazildi", "amber", o.restaurant_id)
    await order_changed(db, o, status_changed=True)
    await courier_changed(db, c)


async def expire_courier_offers(db, c: Courier):
    for of in (await db.execute(select(OrderOffer).where(OrderOffer.courier_id == c.id,
                                                         OrderOffer.result == "pending"))).scalars():
        of.result = "expired"


async def auto_reassign_vehicle(db):
    now = now_utc()
    rows = (await db.execute(select(OrderIssue).where(OrderIssue.ended_at.is_(None), OrderIssue.kind == "vehicle",
                                                      OrderIssue.auto_at <= now))).scalars().all()
    for i in rows:
        o = await db.get(Order, i.order_id)
        if o and o.status in ("assigned", "onway"):
            await reassign_order(db, o, "tizim (avtomatik)")
        else:
            i.ended_at, i.resolved_by = now, "tizim (avtomatik)"


# ---------- Dispatcher sikli ----------
async def dispatch_cycle(db) -> dict:
    now = now_utc()
    stats = {"offers": 0, "queued": 0, "expired": 0}
    # 1. muddati o'tgan takliflar
    for of in (await db.execute(select(OrderOffer).where(OrderOffer.result == "pending",
                                                         OrderOffer.expires_at <= now))).scalars().all():
        c = await db.get(Courier, of.courier_id)
        await decline_offer(db, of, c, expired=True)
        stats["expired"] += 1

    orders = (await db.execute(select(Order).where(Order.status == "new", Order.pay_status != "pending")
                               .order_by(Order.created_at))).scalars().all()
    if not orders:
        return stats
    couriers = (await db.execute(select(Courier).where(Courier.account_status == "active"))).scalars().all()
    issue_c = set((await db.execute(select(OrderIssue.courier_id).where(OrderIssue.ended_at.is_(None)))).scalars())
    pending = (await db.execute(select(OrderOffer).where(OrderOffer.result == "pending"))).scalars().all()
    offered_orders = {p.order_id for p in pending}
    offered_couriers = {p.courier_id for p in pending}
    qlen = dict((await db.execute(select(Order.courier_id, func.count()).where(
        Order.queued.is_(True), Order.status == "assigned").group_by(Order.courier_id))).all())
    cur_ids = [c.current_order_id for c in couriers if c.current_order_id]
    cur_orders = {o.id: o for o in (await db.execute(select(Order).where(Order.id.in_(cur_ids)))).scalars()} \
        if cur_ids else {}
    rests = {r.id: r for r in (await db.execute(select(Restaurant))).scalars()}

    for o in orders:
        if o.id in offered_orders:
            continue
        started = o.search_started_at or o.created_at
        age = (now - started).total_seconds()
        if age >= RESTART_AFTER:
            o.declined_courier_ids, o.search_started_at = [], now
            age = 0
        rest = rests[o.restaurant_id]
        declined = set(o.declined_courier_ids or [])
        idle = [c for c in couriers if c.work_status == "idle" and c.current_order_id is None
                and c.id not in offered_couriers and not qlen.get(c.id) and c.id not in declined
                and can_take(c, o, c.id in issue_c)]
        if idle:
            c = min(idle, key=lambda x: haversine(x.lat, x.lng, rest.lat, rest.lng))
            db.add(OrderOffer(order_id=o.id, courier_id=c.id, offered_at=now,
                              expires_at=now + timedelta(seconds=OFFER_TTL), result="pending"))
            offered_couriers.add(c.id)
            stats["offers"] += 1
            await order_changed(db, o)
            continue
        if age >= QUEUE_AFTER:
            busy = [c for c in couriers if c.work_status in ("delivering", "pickup") and c.current_order_id
                    and not qlen.get(c.id) and c.id not in declined and can_take(c, o, c.id in issue_c)]
            if busy:
                def dist(c):
                    co = cur_orders.get(c.current_order_id)
                    cust = (co.lat, co.lng) if co else None
                    return candidate_distance(c, rest, cust, qlen.get(c.id, 0))
                c = min(busy, key=dist)
                qlen[c.id] = 1
                await queue_to_courier(db, o, c, 1)
                stats["queued"] += 1
    return stats
