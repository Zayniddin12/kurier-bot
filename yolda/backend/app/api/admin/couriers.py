import re
from datetime import timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import ISSUES, LEDGER_TYPES, TRANSPORTS, settings
from app.db import get_db
from app.deps import ops_user
from app.errors import ApiError
from app.models import Courier, LedgerEntry, Order, OrderIssue, OrderOffer, User
from app.schemas.admin import CourierIn, CourierPatch, LedgerIn
from app.services import dispatch, ledger, stats
from app.services.details import order_detail
from app.services.eta import compute_eta
from app.services.events import commit, feed
from app.services.live import courier_changed
from app.services.serializers import courier_row, now_utc, order_row
from app.models import Restaurant

router = APIRouter(tags=["couriers"])

SORTS = {
    "name": lambda r: r["full_name"].lower(), "phone": lambda r: r["phone"], "pinfl": lambda r: r["pinfl"],
    "vehicle": lambda r: r["vehicle"], "balance": lambda r: r["balance"], "today": lambda r: r["today_orders"],
    "created": lambda r: r["created_at"], "status": lambda r: ["delivering", "pickup", "idle", "break", "offline"].index(r["work_status"]),
}


def ledger_item(e: LedgerEntry) -> dict:
    lab, color = LEDGER_TYPES[e.type]
    return {"id": e.id, "type": e.type, "type_label": lab, "color": color, "amount": e.amount, "order_id": e.order_id,
            "note": e.note, "created_at": e.created_at.isoformat()}


async def today_map(db) -> dict:
    t0 = stats.day_start(now_utc().astimezone(stats.TZ).date())
    rows = (await db.execute(select(Order.courier_id, func.count(), func.coalesce(func.sum(Order.total), 0)).where(
        Order.status == "delivered", Order.delivered_at >= t0).group_by(Order.courier_id))).all()
    return {cid: (n, s) for cid, n, s in rows}


async def row_for(db, c: Courier) -> dict:
    tm = await today_map(db)
    i = (await db.execute(select(OrderIssue).where(OrderIssue.courier_id == c.id, OrderIssue.ended_at.is_(None)))).scalars().first()
    o = await db.get(Order, c.current_order_id) if c.current_order_id else None
    n, s = tm.get(c.id, (0, 0))
    return courier_row(c, n, s, i, o)


async def get_courier(db, cid: int) -> Courier:
    c = await db.get(Courier, cid)
    if not c:
        raise ApiError(404, "Kuryer topilmadi")
    return c


def norm_phone(p: str) -> str:
    d = re.sub(r"\D", "", p or "")
    if len(d) == 12 and d.startswith("998"):
        d = d[3:]
    return d


@router.get("/couriers")
async def list_couriers(q: str | None = None, phone: str | None = None, pinfl: str | None = None,
                        vehicle: str | None = None, status: str = "all", sort: str = "work", dir: str = "asc",
                        u: User = Depends(ops_user), db: AsyncSession = Depends(get_db)):
    cs = (await db.execute(select(Courier))).scalars().all()
    tm = await today_map(db)
    issues = {i.courier_id: i for i in (await db.execute(select(OrderIssue).where(OrderIssue.ended_at.is_(None)))).scalars()}
    oids = [c.current_order_id for c in cs if c.current_order_id]
    orders = {o.id: o for o in (await db.execute(select(Order).where(Order.id.in_(oids)))).scalars()} if oids else {}
    rows = []
    for c in cs:
        n, s = tm.get(c.id, (0, 0))
        rows.append(courier_row(c, n, s, issues.get(c.id), orders.get(c.current_order_id)))
    stats_ = {"total": len(rows), "line": sum(1 for r in rows if r["account_status"] == "active" and r["line_state"] == "line"),
              "pause": sum(1 for r in rows if r["account_status"] == "active" and r["line_state"] == "pause"),
              "inactive": sum(1 for r in rows if r["account_status"] == "blocked")}
    debt = sum(r["balance"] for r in rows if r["balance"] < 0)

    def ok(r):
        if q and q.lower() not in r["full_name"].lower() and q.lower().lstrip("#") != str(r["number"]):
            return False
        if phone and norm_phone(phone) not in r["phone"]:
            return False
        if pinfl and pinfl not in r["pinfl"]:
            return False
        if vehicle and r["vehicle"] != vehicle:
            return False
        blocked = r["account_status"] == "blocked"
        if status == "blocked":
            return blocked
        if status == "line":
            return not blocked and r["line_state"] == "line"
        if status == "pause":
            return not blocked and r["line_state"] == "pause"
        if status == "offline":
            return not blocked and r["line_state"] == "offline"
        return True

    rows = [r for r in rows if ok(r)]
    key = SORTS.get(sort, SORTS["status"])
    rows.sort(key=key, reverse=(dir == "desc"))
    return {"items": rows, "stats": stats_, "debt_total": debt}


@router.get("/couriers/{cid}")
async def courier_detail(cid: int, u: User = Depends(ops_user), db: AsyncSession = Depends(get_db)):
    c = await get_courier(db, cid)
    row = await row_for(db, c)
    t0 = stats.day_start(now_utc().astimezone(stats.TZ).date())
    deliv = (await db.execute(select(Order).where(Order.courier_id == c.id, Order.status == "delivered",
                                                  Order.delivered_at >= t0))).scalars().all()
    earned = sum(ledger.courier_earning(o.delivery_fee) for o in deliv)
    cash = sum(o.total for o in deliv if o.pay_method == "Naqd")
    km = round(sum(o.distance_km or 0 for o in deliv), 1)
    led = (await db.execute(select(LedgerEntry).where(LedgerEntry.courier_id == c.id)
                            .order_by(LedgerEntry.id.desc()).limit(8))).scalars().all()
    order = await db.get(Order, c.current_order_id) if c.current_order_id else None
    detail = await order_detail(db, order) if order else None
    queue = (await db.execute(select(Order, Restaurant).join(Restaurant, Restaurant.id == Order.restaurant_id).where(
        Order.courier_id == c.id, Order.queued.is_(True), Order.status == "assigned")
        .order_by(Order.queue_position))).all()
    offer = (await db.execute(select(OrderOffer).where(OrderOffer.courier_id == c.id, OrderOffer.result == "pending",
                                                       OrderOffer.expires_at > now_utc()))).scalars().first()
    shift_min = int((now_utc() - c.online_since).total_seconds() // 60) if c.online_since and c.work_status != "offline" else None
    return {"courier": row, "today": {"earned": earned, "cash": cash, "delivered": len(deliv), "km": km,
                                      "shift_minutes": shift_min},
            "ledger": [ledger_item(e) for e in led], "order": detail,
            "issue": detail["issue"] if detail else None, "eta": detail["eta"] if detail else None,
            "queue": [order_row(o, r, c) for o, r in queue],
            "offer": {"id": offer.id, "order_id": offer.order_id} if offer else None,
            "limit": settings.CASH_LIMIT, "max_km": TRANSPORTS[c.vehicle]["max_km"]}


@router.post("/couriers", status_code=201)
async def create_courier(body: CourierIn, u: User = Depends(ops_user), db: AsyncSession = Depends(get_db)):
    fn, ln = body.first_name.strip(), body.last_name.strip()
    if not fn or not ln:
        raise ApiError(422, "Ism va familiyani kiriting", "name")
    ph = norm_phone(body.phone)
    if len(ph) != 9:
        raise ApiError(422, "Telefon raqami 9 ta raqamdan iborat bo'lsin", "phone")
    pf = re.sub(r"\D", "", body.pinfl or "")
    if len(pf) != 14:
        raise ApiError(422, "JShShIR 14 ta raqamdan iborat bo'lsin", "pinfl")
    if body.vehicle not in TRANSPORTS:
        raise ApiError(422, "Transport turi noto'g'ri", "vehicle")
    if (await db.execute(select(Courier.id).where(Courier.pinfl == pf))).first():
        raise ApiError(422, "Bu JShShIR bilan kuryer allaqachon bor", "pinfl")
    num = ((await db.execute(select(func.max(Courier.number)))).scalar() or 179) + 1
    c = Courier(number=num, first_name=fn, last_name=ln, phone=ph, pinfl=pf, vehicle=body.vehicle,
                plate="—", shift=body.shift, rating=5.0, balance=0, account_status="active", work_status="offline",
                avatar_seed=num * 7 + len(fn), is_female=False)
    db.add(c)
    await db.commit()
    return await row_for(db, c)


@router.patch("/couriers/{cid}")
async def patch_courier(cid: int, body: CourierPatch, u: User = Depends(ops_user), db: AsyncSession = Depends(get_db)):
    c = await get_courier(db, cid)
    d = body.model_dump(exclude_unset=True)
    if "phone" in d:
        ph = norm_phone(d["phone"])
        if len(ph) != 9:
            raise ApiError(422, "Telefon raqami 9 ta raqamdan iborat bo'lsin", "phone")
        d["phone"] = ph
    if "vehicle" in d and d["vehicle"] not in TRANSPORTS:
        raise ApiError(422, "Transport turi noto'g'ri", "vehicle")
    for k, v in d.items():
        setattr(c, k, v)
    await commit(db)
    return await row_for(db, c)


@router.post("/couriers/{cid}/unlink-telegram")
async def unlink_telegram(cid: int, u: User = Depends(ops_user), db: AsyncSession = Depends(get_db)):
    c = await get_courier(db, cid)
    c.telegram_id = None
    await commit(db)
    return await row_for(db, c)


@router.post("/couriers/{cid}/block")
async def block(cid: int, u: User = Depends(ops_user), db: AsyncSession = Depends(get_db)):
    c = await get_courier(db, cid)
    queued = (await db.execute(select(func.count()).select_from(Order).where(
        Order.courier_id == c.id, Order.status.in_(("assigned", "onway"))))).scalar_one()
    if c.current_order_id or queued:
        raise ApiError(409, "Kuryerda faol buyurtma bor — avval yakunlansin")
    c.account_status, c.work_status, c.idle_since = "blocked", "offline", None
    await dispatch.expire_courier_offers(db, c)
    await courier_changed(db, c)
    await commit(db)
    return await row_for(db, c)


@router.post("/couriers/{cid}/unblock")
async def unblock(cid: int, u: User = Depends(ops_user), db: AsyncSession = Depends(get_db)):
    c = await get_courier(db, cid)
    c.account_status = "active"
    await courier_changed(db, c)
    await commit(db)
    return await row_for(db, c)


@router.post("/couriers/{cid}/ledger")
async def add_ledger(cid: int, body: LedgerIn, u: User = Depends(ops_user), db: AsyncSession = Depends(get_db)):
    c = await get_courier(db, cid)
    if body.type not in ("topup", "fix", "payout", "penalty"):
        raise ApiError(422, "Operatsiya turi noto'g'ri", "type")
    if body.amount <= 0:
        raise ApiError(422, "Summani kiriting", "amount")
    sign = -1 if body.type in ("payout", "penalty") else 1
    e = await ledger.add_entry(db, c, body.type, sign * body.amount, None, body.note, u.id)
    await db.flush()
    await courier_changed(db, c)
    from app.services.events import emit
    emit(db, "alerts.changed", {}, None)
    await commit(db)
    return {"courier": await row_for(db, c), "entry": ledger_item(e)}
