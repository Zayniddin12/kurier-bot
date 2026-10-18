from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import String, and_, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import current_user, scope_rid
from app.errors import ApiError
from app.models import Courier, Order, Restaurant, User
from app.schemas.admin import CancelIn
from app.services import dispatch, stats
from app.services.details import order_detail
from app.services.events import commit, flush_events
from app.services.orders import OrderError, cancel_order
from app.services.serializers import order_row

router = APIRouter(tags=["orders"])


async def load_order(db, u: User, oid: int) -> Order:
    o = await db.get(Order, oid)
    if not o or (u.role == "restaurant_staff" and o.restaurant_id != u.restaurant_id):
        raise ApiError(404, "Buyurtma topilmadi")
    return o


@router.get("/orders")
async def list_orders(period: str = "today", from_: date | None = Query(None, alias="from"), to: date | None = None,
                      restaurant_id: int | None = None, status: str = "all", pay: str | None = None, q: str | None = None,
                      page: int = 1, per_page: int = 20, u: User = Depends(current_user),
                      db: AsyncSession = Depends(get_db)):
    rid = scope_rid(u, restaurant_id)
    p = stats.resolve_period(period, from_, to)
    conds = [Order.created_at >= p["start"], Order.created_at < p["end"]]
    if rid:
        conds.append(Order.restaurant_id == rid)
    if status == "active":
        conds.append(Order.status.in_(("new", "assigned", "onway")))
    elif status in ("delivered", "cancelled"):
        conds.append(Order.status == status)
    if pay in ("Payme", "Click", "Karta", "Naqd"):
        conds.append(Order.pay_method == pay)
    if q and q.strip():
        s = q.strip()
        like = f"%{s}%"
        sub = [Order.external_id.ilike(like), Order.customer_name.ilike(like), Order.address.ilike(like),
               Order.customer_phone.ilike(like), Courier.first_name.ilike(like), Courier.last_name.ilike(like),
               (Courier.first_name + " " + Courier.last_name).ilike(like), Courier.phone.ilike(like)]
        if s.lstrip("#").isdigit():
            sub.append(Order.id == int(s.lstrip("#")))
        conds.append(or_(*sub))
    base = select(Order, Restaurant, Courier).join(Restaurant, Restaurant.id == Order.restaurant_id) \
        .outerjoin(Courier, Courier.id == Order.courier_id).where(and_(*conds))
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    per_page = max(1, min(per_page, 100))
    page = max(1, page)
    rows = (await db.execute(base.order_by(Order.created_at.desc(), Order.id.desc())
                             .limit(per_page).offset((page - 1) * per_page))).all()
    allq = select(*stats.COLS).join(Restaurant, Restaurant.id == Order.restaurant_id) \
        .outerjoin(Courier, Courier.id == Order.courier_id).where(and_(*conds))
    allrows = (await db.execute(allq)).all()
    return {"items": [order_row(o, r, c) for o, r, c in rows], "total": total, "page": page, "per_page": per_page,
            "summary": stats.summary_for(allrows), "chart": stats.delivered_other_chart(allrows, p)}


@router.get("/orders/{oid}")
async def get_order(oid: int, u: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    return await order_detail(db, await load_order(db, u, oid))


@router.post("/orders/{oid}/cancel")
async def cancel(oid: int, body: CancelIn, u: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    o = await load_order(db, u, oid)
    try:
        refunded = await cancel_order(db, o, body.reason.strip())
    except OrderError as e:
        raise ApiError(e.status, e.message)
    await commit(db)
    return {"order": await order_detail(db, o), "refunded": refunded}


@router.post("/orders/{oid}/issue/resolve")
async def resolve(oid: int, u: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    o = await load_order(db, u, oid)
    try:
        await dispatch.resolve_issue(db, o, "operator")
    except OrderError as e:
        raise ApiError(e.status, e.message)
    await commit(db)
    return {"order": await order_detail(db, o)}


@router.post("/orders/{oid}/issue/reassign")
async def reassign(oid: int, u: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    o = await load_order(db, u, oid)
    try:
        await dispatch.reassign_order(db, o, "operator")
    except OrderError as e:
        raise ApiError(e.status, e.message)
    await commit(db)
    return {"order": await order_detail(db, o)}


@router.post("/orders/{oid}/notify-customer")
async def notify(oid: int, u: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    await load_order(db, u, oid)
    return {"ok": True}
