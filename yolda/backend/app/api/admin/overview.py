from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import current_user, forced_rid, scope_rid
from app.models import DismissedAlert, FeedEvent, User, Courier, Restaurant
from app.services import stats
from app.services.alerts import build_alerts
from app.services.events import commit, emit, feed_row
from app.services.live import map_entry
from app.services.serializers import restaurant_row
from app.errors import ApiError
from app.models import Order, OrderIssue

router = APIRouter(tags=["overview"])


@router.get("/overview")
async def overview(period: str = "today", from_: date | None = Query(None, alias="from"),
                   to: date | None = None, restaurant_id: int | None = None,
                   u: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    return await stats.overview(db, period, from_, to, scope_rid(u, restaurant_id), forced_rid(u))


@router.get("/alerts")
async def alerts(restaurant_id: int | None = None, u: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    items = await build_alerts(db, u, scope_rid(u, restaurant_id))
    return {"items": items, "count": len(items)}


@router.post("/alerts/{key}/dismiss")
async def dismiss(key: str, u: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    if key.startswith("issue:"):
        raise ApiError(409, "Bu ogohlantirishni yopib bo'lmaydi")
    if not await db.get(DismissedAlert, (u.id, key)):
        db.add(DismissedAlert(user_id=u.id, alert_key=key))
        await db.commit()
    return {"ok": True}


@router.get("/feed")
async def get_feed(limit: int = 60, restaurant_id: int | None = None, u: User = Depends(current_user),
                   db: AsyncSession = Depends(get_db)):
    rid = scope_rid(u, restaurant_id)
    q = select(FeedEvent).order_by(FeedEvent.id.desc()).limit(min(limit, 200))
    if rid:
        q = q.where(FeedEvent.restaurant_id == rid)
    return {"items": [feed_row(e) for e in (await db.execute(q)).scalars()]}


@router.get("/map/state")
async def map_state(restaurant_id: int | None = None, u: User = Depends(current_user),
                    db: AsyncSession = Depends(get_db)):
    rid = scope_rid(u, restaurant_id)
    rests = (await db.execute(select(Restaurant).order_by(Restaurant.id))).scalars().all()
    rmap = {r.id: r for r in rests}
    couriers = (await db.execute(select(Courier).where(Courier.account_status == "active"))).scalars().all()
    oids = [c.current_order_id for c in couriers if c.current_order_id]
    orders = {o.id: o for o in (await db.execute(select(Order).where(Order.id.in_(oids)))).scalars()} if oids else {}
    issues = {i.order_id: i for i in (await db.execute(select(OrderIssue).where(
        OrderIssue.ended_at.is_(None)))).scalars()}
    out = []
    for c in couriers:
        o = orders.get(c.current_order_id)
        if u.role == "restaurant_staff" and (not o or o.restaurant_id != u.restaurant_id):
            continue
        out.append(map_entry(c, o, rmap.get(o.restaurant_id) if o else None, issues.get(o.id) if o else None))
    visible = [r for r in rests if not (u.role == "restaurant_staff" and r.id != u.restaurant_id)]
    return {"couriers": out, "restaurants": [restaurant_row(r) for r in visible]}
