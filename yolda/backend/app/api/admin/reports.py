from collections import defaultdict
from datetime import timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin.couriers import get_courier, row_for
from app.config import settings
from app.db import get_db
from app.deps import ops_user
from app.models import Courier, Order, User
from app.services import ledger, stats
from app.services.events import commit, emit
from app.services.live import courier_changed
from app.services.serializers import courier_brief, iso, now_utc

router = APIRouter(tags=["reports"])


@router.get("/reports/courier-income")
async def income(days: int = 1, u: User = Depends(ops_user), db: AsyncSession = Depends(get_db)):
    days = days if days in (1, 7, 30) else 1
    t0 = stats.day_start(now_utc().astimezone(stats.TZ).date())
    start = t0 - timedelta(days=days - 1)
    orders = (await db.execute(select(Order).where(Order.status == "delivered", Order.delivered_at >= start,
                                                   Order.courier_id.is_not(None)))).scalars().all()
    agg = defaultdict(lambda: {"delivered": 0, "amount": 0, "cash": 0, "earned": 0, "commission": 0})
    for o in orders:
        a = agg[o.courier_id]
        a["delivered"] += 1
        a["amount"] += o.total
        a["cash"] += o.total if o.pay_method == "Naqd" else 0
        a["earned"] += ledger.courier_earning(o.delivery_fee)
        a["commission"] += ledger.platform_commission(o.delivery_fee)
    cs = {c.id: c for c in (await db.execute(select(Courier).where(Courier.id.in_(list(agg))))).scalars()} if agg else {}
    items = [{"courier": courier_brief(cs[i]), **a} for i, a in sorted(agg.items(), key=lambda kv: -kv[1]["earned"])]
    totals = {k: sum(x[k] for x in items) for k in ("delivered", "amount", "cash", "earned", "commission")}
    return {"from": start.date().isoformat(), "to": t0.date().isoformat(), "days": days, "items": items, "totals": totals}


@router.get("/reports/salary")
async def salary(u: User = Depends(ops_user), db: AsyncSession = Depends(get_db)):
    cs = (await db.execute(select(Courier).where(Courier.account_status == "active").order_by(Courier.number))).scalars().all()
    items = []
    for c in cs:
        s = await ledger.settle_numbers(db, c)
        items.append({"courier": courier_brief(c), "settled_at": iso(c.settled_at), "deliveries": s["deliveries"],
                      "earned": s["earned"], "bonus": s["bonus"], "fine": s["fine"], "late": s["late"],
                      "balance": c.balance, "payable": s["payable"]})
    return {"items": items, "total_payable": sum(i["payable"] for i in items),
            "rules": {"commission": settings.COMMISSION, "bonus_per_10": settings.BONUS_PER_10,
                      "late_fine": settings.LATE_FINE, "sla": settings.SLA, "cash_limit": settings.CASH_LIMIT}}


@router.post("/couriers/settle-all")
async def settle_all(u: User = Depends(ops_user), db: AsyncSession = Depends(get_db)):
    cs = (await db.execute(select(Courier).where(Courier.account_status == "active"))).scalars().all()
    total, n = 0, 0
    for c in cs:
        paid = await ledger.settle(db, c, u.id)
        total += paid
        n += 1 if paid > 0 else 0
        await courier_changed(db, c)
    emit(db, "alerts.changed", {}, None)
    await commit(db)
    return {"paid_total": total, "count": n}


@router.post("/couriers/{cid}/settle")
async def settle_one(cid: int, u: User = Depends(ops_user), db: AsyncSession = Depends(get_db)):
    c = await get_courier(db, cid)
    paid = await ledger.settle(db, c, u.id)
    await courier_changed(db, c)
    emit(db, "alerts.changed", {}, None)
    await commit(db)
    return {"paid": paid, "courier": await row_for(db, c)}
