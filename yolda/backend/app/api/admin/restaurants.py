from collections import defaultdict
from datetime import timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import check_rest_access, current_user, ops_user
from app.errors import ApiError
from app.models import Order, OrderItem, Restaurant, User
from app.schemas.admin import PauseIn, RestaurantIn, RestaurantPatch
from app.security import hash_key, new_api_key, new_webhook_secret
from app.services import stats
from app.services.events import commit, emit, esc, feed
from app.services.serializers import iso, now_utc, order_row, restaurant_row
from app.models import Courier

router = APIRouter(tags=["restaurants"])
PALETTE = ["#E4572E", "#2E8B57", "#E8871E", "#C0392B", "#8E44AD", "#138A72", "#2E6BD8", "#7F5539", "#5E8C45", "#A85F1F"]


async def counts(db) -> dict:
    t0 = stats.day_start(now_utc().astimezone(stats.TZ).date())
    today = dict((await db.execute(select(Order.restaurant_id, func.count()).where(Order.created_at >= t0)
                                   .group_by(Order.restaurant_id))).all())
    active = dict((await db.execute(select(Order.restaurant_id, func.count()).where(
        Order.status.in_(("new", "assigned", "onway"))).group_by(Order.restaurant_id))).all())
    return {"today": today, "active": active}


async def row(db, r: Restaurant) -> dict:
    c = await counts(db)
    return restaurant_row(r, c["today"].get(r.id, 0), c["active"].get(r.id, 0))


async def load(db, u, rid: int) -> Restaurant:
    r = await db.get(Restaurant, rid)
    if not r:
        raise ApiError(404, "Restoran topilmadi")
    check_rest_access(u, rid)
    return r


@router.get("/restaurants")
async def list_restaurants(q: str | None = None, status: str = "all", u: User = Depends(current_user),
                           db: AsyncSession = Depends(get_db)):
    rs = (await db.execute(select(Restaurant).order_by(Restaurant.id))).scalars().all()
    if u.role == "restaurant_staff":
        rs = [r for r in rs if r.id == u.restaurant_id]
    c = await counts(db)
    rows = [restaurant_row(r, c["today"].get(r.id, 0), c["active"].get(r.id, 0)) for r in rs]
    cnt = {"all": len(rows), "open": sum(1 for r in rows if r["status"] == "open"),
           "paused": sum(1 for r in rows if r["status"] == "paused")}
    if q:
        ql = q.lower()
        rows = [r for r in rows if ql in r["name"].lower() or ql in r["district"].lower() or ql in r["cuisine"].lower()]
    if status in ("open", "paused"):
        rows = [r for r in rows if r["status"] == status]
    return {"items": rows, "counts": cnt}


@router.get("/restaurants/{rid}")
async def detail(rid: int, u: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    r = await load(db, u, rid)
    now = now_utc().astimezone(stats.TZ)
    start = stats.day_start(now.date()) - timedelta(days=6)
    rows = await stats.fetch(db, start, start + timedelta(days=7), rid)
    vals = [0] * 7
    for o in rows:
        vals[(stats.local(o.created_at).date() - start.date()).days] += 1
    labels = [stats.weekday_name(start.date() + timedelta(days=i)) for i in range(7)]
    top = (await db.execute(select(OrderItem.name, func.sum(OrderItem.qty).label("n")).join(
        Order, Order.id == OrderItem.order_id).where(Order.restaurant_id == rid, Order.status != "cancelled",
                                                     Order.created_at >= now_utc() - timedelta(days=30))
        .group_by(OrderItem.name).order_by(func.sum(OrderItem.qty).desc()).limit(5))).all()
    act = (await db.execute(select(Order, Courier).outerjoin(Courier, Courier.id == Order.courier_id).where(
        Order.restaurant_id == rid, Order.status.in_(("new", "assigned", "onway"))).order_by(Order.created_at.desc()))).all()
    rr = await row(db, r)
    ok = rr["sync_ok"]
    return {"restaurant": rr, "week": {"labels": labels, "values": vals},
            "top_items": [{"name": n, "qty": int(q)} for n, q in top],
            "active_orders": [order_row(o, r, c) for o, c in act],
            "integration": {"type": r.integration_type, "pos_system": r.pos_system, "ok": ok,
                            "status_text": "Ulangan, ishlayapti" if ok else "Aloqa yo'q",
                            "last_sync_at": iso(r.last_sync_at), "api_key_prefix": r.api_key_prefix,
                            "webhook_url": r.webhook_url}}


@router.post("/restaurants", status_code=201)
async def create(body: RestaurantIn, u: User = Depends(ops_user), db: AsyncSession = Depends(get_db)):
    n = (await db.execute(select(func.count()).select_from(Restaurant))).scalar_one()
    if body.api_key:
        key, generated = body.api_key, False
        prefix, h = key[:12], hash_key(key)
        if (await db.execute(select(Restaurant.id).where(Restaurant.api_key_hash == h))).first():
            raise ApiError(409, "Bu API kalit boshqa restoranga ulangan", "api_key")
    else:
        (key, prefix, h), generated = new_api_key(), True
    secret = new_webhook_secret() if body.webhook_url else None
    r = Restaurant(name=body.name.strip(), cuisine=body.cuisine, district=body.district, address=body.address,
                   lat=body.lat, lng=body.lng, color=body.color or PALETTE[n % len(PALETTE)],
                   integration_type=body.integration_type, pos_system=body.pos_system, phone=body.phone,
                   hours=body.hours, manager=body.manager, webhook_url=body.webhook_url or None,
                   webhook_secret=secret, api_key_prefix=prefix, api_key_hash=h, status="open", rating=5.0,
                   prep_minutes=15)
    db.add(r)
    await db.flush()
    await feed(db, f"Yangi restoran ulandi: <b>{esc(r.name)}</b>", "violet", r.id)
    emit(db, "restaurant.updated", restaurant_row(r), None)
    await commit(db)
    # o'zi bergan kalitni qayta ko'rsatmaymiz
    return {"restaurant": restaurant_row(r), "api_key": key if generated else None, "webhook_secret": secret}


@router.patch("/restaurants/{rid}")
async def patch(rid: int, body: RestaurantPatch, u: User = Depends(ops_user), db: AsyncSession = Depends(get_db)):
    r = await load(db, u, rid)
    secret = None
    for k, v in body.model_dump(exclude_unset=True).items():
        if k == "webhook_url":
            v = v or None
            if v and not r.webhook_secret:
                secret = r.webhook_secret = new_webhook_secret()
        setattr(r, k, v)
    emit(db, "restaurant.updated", restaurant_row(r), r.id)
    await commit(db)
    return {"restaurant": await row(db, r), "webhook_secret": secret}


@router.post("/restaurants/{rid}/pause")
async def pause(rid: int, body: PauseIn, u: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    r = await load(db, u, rid)
    r.status, r.pause_reason = "paused", body.reason.strip() or None
    await feed(db, f"<b>{esc(r.name)}</b> buyurtma qabul qilishni to'xtatdi", "amber", r.id)
    emit(db, "restaurant.updated", restaurant_row(r), r.id)
    emit(db, "alerts.changed", {}, None)
    await commit(db)
    return await row(db, r)


@router.post("/restaurants/{rid}/resume")
async def resume(rid: int, u: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    r = await load(db, u, rid)
    r.status, r.pause_reason = "open", None
    await feed(db, f"<b>{esc(r.name)}</b> qayta buyurtma qabul qilmoqda", "teal", r.id)
    emit(db, "restaurant.updated", restaurant_row(r), r.id)
    emit(db, "alerts.changed", {}, None)
    await commit(db)
    return await row(db, r)


@router.post("/restaurants/{rid}/rotate-key")
async def rotate(rid: int, u: User = Depends(ops_user), db: AsyncSession = Depends(get_db)):
    r = await load(db, u, rid)
    key, prefix, h = new_api_key()
    r.api_key_prefix, r.api_key_hash = prefix, h
    await commit(db)
    return {"api_key": key, "api_key_prefix": prefix}
