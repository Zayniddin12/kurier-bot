"""Operator uchun "Buyurtmalar navbati" sahifasi: ro'yxat, hisoblagichlar, tafsilot va qo'lda boshqarish."""
import secrets
from datetime import timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import ISSUES, LEDGER_TYPES, TRANSPORTS, VENDOR_LEDGER_TYPES, settings
from app.db import get_db
from app.deps import ops_user
from app.errors import ApiError
from app.models import (BlockedCustomer, Courier, CustomerNote, LedgerEntry, Order, OrderIssue, OrderLog, OrderOffer,
                        Restaurant, User, VendorLedgerEntry)
from app.menus import menu_for
from app.schemas.admin import AssignIn, BlockIn, CustomerNoteIn, OperatorOrderIn, OrderNotesIn
from app.services import alerts, dispatch, routing, stats
from app.services.details import order_detail
from app.services.events import commit, esc, feed
from app.services.geo import ROAD_FACTOR, haversine
from app.services.live import courier_changed
from app.services import orders as osvc
from app.services.geo import road_km
from app.services.ledger import delivery_fee_for
from app.services.orders import OrderError, order_changed, set_payment
from app.services.serializers import full_name, iso, now_utc, order_row

router = APIRouter(prefix="/operator", tags=["operator"])

ACTIVE = ("new", "assigned", "onway")
CHIPS = ("all", "attention", "nocourier", "new", "assigned", "onway", "done")
NEW_WINDOW_S = 300           # "Yangi" chipi: oxirgi 5 daqiqada tushgan, hali kuryersiz buyurtmalar
NOCOURIER_ATTENTION_S = 120  # kuryer topilmasa 2 daqiqadan keyin "Diqqat"


async def load_order(db, oid: int) -> Order:
    o = await db.get(Order, oid)
    if not o:
        raise ApiError(404, "Buyurtma topilmadi")
    return o


async def log(db, o: Order, u: User, text: str):
    db.add(OrderLog(order_id=o.id, actor=u.full_name or u.email, text=text[:500]))


def attention_reason(x: dict, now) -> str | None:
    o, iss, eta = x["order"], x["issue"], x["eta"]
    if iss:
        return ISSUES[iss.kind]["text"]
    if eta and eta["late"]:
        return f"Kechikmoqda · jami ~{eta['total_min']} daq"
    if o.status == "new" and o.pay_status != "pending" and (now - o.created_at).total_seconds() >= NOCOURIER_ATTENTION_S:
        return "Mos kuryer topilmadi"
    return None


def active_item(x: dict, now) -> dict:
    o, c, r, eta = x["order"], x["courier"], x["rest"], x["eta"]
    d = order_row(o, r, c)
    reason = attention_reason(x, now)
    d.update({"attention": reason, "issue_text": ISSUES[x["issue"].kind]["text"] if x["issue"] else None,
              "cancel_reason": None, "eta_late": bool(eta and eta["late"]), "pay_pending": o.pay_status == "pending"})
    return d


def done_item(o, r, c) -> dict:
    d = order_row(o, r, c)
    d.update({"attention": None, "issue_text": None, "cancel_reason": o.cancel_reason, "eta_late": False,
              "pay_pending": False})
    return d


def chip_match(chip: str, x: dict, now) -> bool:
    o = x["order"]
    if chip == "all":
        return True
    if chip == "attention":
        return attention_reason(x, now) is not None
    if chip == "nocourier":
        return o.status == "new"
    if chip == "new":
        return o.status == "new" and (now - o.created_at).total_seconds() < NEW_WINDOW_S
    return o.status == chip


@router.get("/queue")
async def queue(chip: str = "all", sub: str = "all", courier_id: int | None = None, restaurant_id: int | None = None,
                q: str | None = None, page: int = 1, per_page: int = 20, u: User = Depends(ops_user),
                db: AsyncSession = Depends(get_db)):
    now = now_utc()
    chip = chip if chip in CHIPS else "all"
    per_page, page = max(1, min(per_page, 100)), max(1, page)
    ctx = await alerts.active_context(db, restaurant_id, now)
    if courier_id:
        ctx = [x for x in ctx if x["order"].courier_id == courier_id]

    t0 = stats.day_start(now.astimezone(stats.TZ).date())
    fin = func.coalesce(Order.delivered_at, Order.cancelled_at)
    dconds = [Order.status.in_(("delivered", "cancelled")), fin >= t0]
    if restaurant_id:
        dconds.append(Order.restaurant_id == restaurant_id)
    if courier_id:
        dconds.append(Order.courier_id == courier_id)
    done_by = dict((await db.execute(select(Order.status, func.count()).where(and_(*dconds)).group_by(Order.status))).all())
    idle = (await db.execute(select(func.count()).select_from(Courier).where(
        Courier.account_status == "active", Courier.work_status == "idle"))).scalar_one()
    counts = {
        "active": len(ctx), "attention": sum(1 for x in ctx if attention_reason(x, now)),
        "nocourier": sum(1 for x in ctx if x["order"].status == "new"),
        "new": sum(1 for x in ctx if chip_match("new", x, now)),
        "assigned": sum(1 for x in ctx if x["order"].status == "assigned"),
        "onway": sum(1 for x in ctx if x["order"].status == "onway"),
        "done": sum(done_by.values()), "done_delivered": done_by.get("delivered", 0),
        "done_cancelled": done_by.get("cancelled", 0), "idle_couriers": idle,
    }

    if q and q.strip():  # qidiruv: butun tarix bo'yicha
        s = q.strip()
        like = f"%{s}%"
        sub_c = [Order.external_id.ilike(like), Order.customer_name.ilike(like), Order.customer_phone.ilike(like),
                 Restaurant.name.ilike(like), Courier.first_name.ilike(like), Courier.last_name.ilike(like),
                 (Courier.first_name + " " + Courier.last_name).ilike(like)]
        if s.lstrip("#").isdigit():
            sub_c.append(Order.id == int(s.lstrip("#")))
        conds = [or_(*sub_c)]
        if restaurant_id:
            conds.append(Order.restaurant_id == restaurant_id)
        if courier_id:
            conds.append(Order.courier_id == courier_id)
        base = select(Order, Restaurant, Courier).join(Restaurant, Restaurant.id == Order.restaurant_id) \
            .outerjoin(Courier, Courier.id == Order.courier_id).where(and_(*conds))
        total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
        rows = (await db.execute(base.order_by(Order.created_at.desc(), Order.id.desc())
                                 .limit(per_page).offset((page - 1) * per_page))).all()
        by_id = {x["order"].id: x for x in ctx}
        items = [active_item(by_id[o.id], now) if o.id in by_id else done_item(o, r, c) for o, r, c in rows]
    elif chip == "done":
        conds = list(dconds)
        if sub in ("delivered", "cancelled"):
            conds.append(Order.status == sub)
        base = select(Order, Restaurant, Courier).join(Restaurant, Restaurant.id == Order.restaurant_id) \
            .outerjoin(Courier, Courier.id == Order.courier_id).where(and_(*conds))
        total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
        rows = (await db.execute(base.order_by(fin.desc(), Order.id.desc())
                                 .limit(per_page).offset((page - 1) * per_page))).all()
        items = [done_item(o, r, c) for o, r, c in rows]
    else:
        sel = [x for x in ctx if chip_match(chip, x, now)]
        # diqqat talab qiladiganlar yuqorida, keyin eng eskisi birinchi
        sel.sort(key=lambda x: (attention_reason(x, now) is None, x["order"].created_at))
        total = len(sel)
        items = [active_item(x, now) for x in sel[(page - 1) * per_page: page * per_page]]
    return {"counts": counts, "items": items, "total": total, "page": page, "per_page": per_page}


@router.get("/couriers-brief")
async def couriers_brief(u: User = Depends(ops_user), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Courier).where(Courier.account_status == "active")
                             .order_by(Courier.first_name, Courier.last_name))).scalars().all()
    return [{"id": c.id, "name": full_name(c), "number": c.number} for c in rows]


# ---------------- Tafsilot ----------------
STEP_DEFS = (("new", "Qabul qilindi"), ("assigned", "Kuryer biriktirildi"), ("onway", "Yo'lda"), ("delivered", "Yetkazildi"))


def steps_for(o: Order) -> list[dict]:
    cur = {"new": 0, "assigned": 1, "onway": 2, "delivered": 3}.get(o.status, -1)
    out = []
    for i, (k, label) in enumerate(STEP_DEFS):
        state = "todo"
        if o.status == "cancelled":
            state = "off"
        elif i < cur or (i == cur and o.status == "delivered"):
            state = "done"
        elif i == cur:
            state = "current"
        out.append({"key": k, "label": label, "state": state})
    return out


def next_action(o: Order) -> dict | None:
    if o.status == "new":
        if o.pay_status == "pending":
            return {"kind": "confirm_payment", "title": "Onlayn to'lov tasdiqlanishi kutilmoqda",
                    "text": "To'lov tasdiqlanmaguncha tizim kuryer qidirmaydi. To'lov kelganini tekshirib, tasdiqlang.",
                    "button": "To'lovni tasdiqlash"}
        return {"kind": "assign", "title": "Kuryer biriktirilmagan",
                "text": "Tizim mos kuryerni avtomatik qidirmoqda. Kutmasdan o'zingiz kuryer tanlashingiz mumkin.",
                "button": "Kuryer tanlash"}
    if o.status == "assigned":
        if o.queued:
            return None
        return {"kind": "picked", "title": "Kuryer restoranga yo'lda",
                "text": "Kuryer buyurtmani restorandan olgach, \"Yo'lda\" bosqichiga o'tkazing.",
                "button": "Kuryer oldi"}
    if o.status == "onway":
        return {"kind": "delivered", "title": "Kuryer mijozga yo'lda",
                "text": "Mijoz buyurtmani olganini tasdiqlang — buyurtma \"Yetkazildi\" bo'ladi va hisob-kitob yoziladi.",
                "button": "Yetkazildi"}
    return None


def mmss(sec: int | None) -> str | None:
    if sec is None:
        return None
    sec = max(0, int(sec))
    return f"{sec // 60:02d}:{sec % 60:02d}"


def op_timeline(o: Order, offers: list[OrderOffer]) -> list[dict]:
    steps = [("created", "Buyurtma yaratildi", o.created_at)]
    first_offer = min((of.offered_at for of in offers), default=None)
    if first_offer:
        steps.append(("offered", "Kuryerga taklif yuborildi", first_offer))
    steps += [("assigned", "Kuryer biriktirildi", o.assigned_at if o.courier_id and not o.queued else None),
              ("picked", "Kuryer oldi", o.picked_at),
              ("delivered", "Yetkazildi", o.delivered_at)]
    out, prev, cur_set = [], None, o.status in ("delivered", "cancelled")
    for k, label, at in steps:
        if at:
            out.append({"key": k, "label": label, "at": iso(at), "state": "done",
                        "delta": mmss((at - prev).total_seconds()) if prev else None})
            prev = at
        elif not cur_set:
            out.append({"key": k, "label": label, "at": None, "state": "current", "delta": None})
            cur_set = True
        else:
            out.append({"key": k, "label": label, "at": None, "state": "todo", "delta": None})
    if o.status == "cancelled":
        out = [s for s in out if s["state"] == "done"]
        out.append({"key": "cancelled", "label": f"Bekor qilindi: {o.cancel_reason or '—'}", "at": iso(o.cancelled_at),
                    "state": "cancelled", "delta": mmss((o.cancelled_at - prev).total_seconds()) if prev and o.cancelled_at else None})
    return out


async def build_payments(db, o: Order, r: Restaurant) -> list[dict]:
    out = [{"label": f"Mijoz to'lovi · {o.pay_method}", "amount": o.total, "at": iso(o.created_at),
            "note": {"paid": "To'langan", "pending": "Tasdiqlanmoqda", "failed": "To'lov o'tmadi", "cod": "Kuryer naqd oladi",
                     "collected": "Kuryer naqd oldi", "refunded": "Mijozga qaytarildi", "void": "To'lanmagan"}.get(o.pay_status, o.pay_status),
            "side": "customer"}]
    for e in (await db.execute(select(LedgerEntry).where(LedgerEntry.order_id == o.id).order_by(LedgerEntry.created_at))).scalars():
        out.append({"label": f"Kuryer · {LEDGER_TYPES.get(e.type, (e.type,))[0]}", "amount": e.amount, "at": iso(e.created_at),
                    "note": e.note, "side": "courier"})
    for e in (await db.execute(select(VendorLedgerEntry).where(VendorLedgerEntry.order_id == o.id)
                               .order_by(VendorLedgerEntry.created_at))).scalars():
        out.append({"label": f"{r.name} · {VENDOR_LEDGER_TYPES.get(e.type, (e.type,))[0]}", "amount": e.amount,
                    "at": iso(e.created_at), "note": e.note, "side": "vendor"})
    return out


async def build_logs(db, o: Order, offers: list[OrderOffer], issues) -> list[dict]:
    cids = {of.courier_id for of in offers} | ({o.courier_id} if o.courier_id else set())
    names = {c.id: full_name(c) for c in (await db.execute(select(Courier).where(Courier.id.in_(cids)))).scalars()} if cids else {}
    ev = [(o.created_at, "Buyurtma yaratildi", "tizim")]
    res = {"accepted": "qabul qildi", "declined": "rad etdi", "expired": "javob bermadi", "pending": "javob kutilmoqda"}
    for of in offers:
        ev.append((of.offered_at, f"{names.get(of.courier_id, 'Kuryer')} ga taklif yuborildi — {res.get(of.result, of.result)}", "tizim"))
    if o.assigned_at and o.courier_id:
        ev.append((o.assigned_at, f"Kuryer biriktirildi: {names.get(o.courier_id, '—')}" + (" (navbatda)" if o.queued else ""), "tizim"))
    if o.picked_at:
        ev.append((o.picked_at, "Kuryer buyurtmani olib ketdi", "tizim"))
    if o.delivered_at:
        ev.append((o.delivered_at, "Buyurtma yetkazildi", "tizim"))
    if o.cancelled_at:
        ev.append((o.cancelled_at, f"Buyurtma bekor qilindi: {o.cancel_reason or '—'}", "tizim"))
    for i in issues:
        ev.append((i.started_at, f"Muammo: {ISSUES[i.kind]['text']}", "kuryer"))
        if i.ended_at:
            ev.append((i.ended_at, f"Muammo hal qilindi: {ISSUES[i.kind]['text']}", i.resolved_by or "tizim"))
    for lg in (await db.execute(select(OrderLog).where(OrderLog.order_id == o.id))).scalars():
        ev.append((lg.created_at, lg.text, lg.actor or "operator"))
    ev.sort(key=lambda x: x[0], reverse=True)
    return [{"at": iso(a), "text": t, "actor": who} for a, t, who in ev]


async def customer_info(db, o: Order) -> dict:
    ph = o.customer_phone
    rows = dict((await db.execute(select(Order.status, func.count()).where(
        Order.customer_phone == ph, Order.status.in_(("delivered", "cancelled"))).group_by(Order.status))).all())

    async def last(status):
        return (await db.execute(select(Order.id).where(Order.customer_phone == ph, Order.status == status, Order.id != o.id)
                                 .order_by(Order.created_at.desc()).limit(1))).scalar_one_or_none()
    blocked = await db.get(BlockedCustomer, ph)
    notes = (await db.execute(select(CustomerNote).where(CustomerNote.phone == ph)
                              .order_by(CustomerNote.created_at.desc()).limit(10))).scalars().all()
    return {"phone": ph, "name": o.customer_name, "delivered": rows.get("delivered", 0), "cancelled": rows.get("cancelled", 0),
            "last_delivered_id": await last("delivered"), "last_cancelled_id": await last("cancelled"),
            "blocked": bool(blocked), "block_reason": blocked.reason if blocked else None,
            "notes": [{"id": n.id, "text": n.text, "author": n.author, "created_at": iso(n.created_at)} for n in notes]}


async def op_detail(db, o: Order) -> dict:
    d = await order_detail(db, o)
    r = await db.get(Restaurant, o.restaurant_id)
    offers = (await db.execute(select(OrderOffer).where(OrderOffer.order_id == o.id).order_by(OrderOffer.offered_at))).scalars().all()
    issues = (await db.execute(select(OrderIssue).where(OrderIssue.order_id == o.id).order_by(OrderIssue.started_at))).scalars().all()
    end = o.delivered_at or o.cancelled_at or now_utc()
    payments = await build_payments(db, o, r)
    logs = await build_logs(db, o, offers, issues)
    d.update({
        "restaurant_note": o.note, "courier_note": o.courier_note,
        "customer": await customer_info(db, o), "steps": steps_for(o), "next_action": next_action(o),
        "op_timeline": op_timeline(o, offers), "total_seconds": int((end - o.created_at).total_seconds()),
        "payments": payments, "fiscal": [], "logs": logs,
        "can_edit": o.status in ACTIVE, "items_total": sum(i["qty"] * i["price"] for i in d["items"]),
    })
    return d


def _menu_items(r: Restaurant) -> list[dict]:
    return [{"id": i, "name": n, "price": p} for i, (n, p) in enumerate(menu_for(r))]


@router.get("/restaurants/{rid}/menu")
async def restaurant_menu(rid: int, u: User = Depends(ops_user), db: AsyncSession = Depends(get_db)):
    r = await db.get(Restaurant, rid)
    if not r:
        raise ApiError(404, "Restoran topilmadi")
    return {"restaurant_id": r.id, "items": _menu_items(r)}


@router.get("/quote")
async def quote(restaurant_id: int, lat: float = Query(ge=-90, le=90), lng: float = Query(ge=-180, le=180),
                u: User = Depends(ops_user), db: AsyncSession = Depends(get_db)):
    r = await db.get(Restaurant, restaurant_id)
    if not r:
        raise ApiError(404, "Restoran topilmadi")
    km = road_km(r.lat, r.lng, lat, lng)
    return {"distance_km": km, "delivery_fee": delivery_fee_for(km)}


@router.post("/orders", status_code=201)
async def create_operator_order(body: OperatorOrderIn, u: User = Depends(ops_user), db: AsyncSession = Depends(get_db)):
    """Operator qo'lda buyurtma yaratadi. To'lov har doim naqd: mijoz kuryerga o'zi to'laydi."""
    r = await db.get(Restaurant, body.restaurant_id)
    if not r:
        raise ApiError(404, "Restoran topilmadi")
    menu = {m["id"]: m for m in _menu_items(r)}
    items = []
    for it in body.items:
        m = menu.get(it.menu_id)
        if not m:
            raise ApiError(422, "Menyuda bunday taom yo'q")
        items.append({"name": m["name"], "qty": it.qty, "price": m["price"]})
    ext = f"OP-{now_utc():%y%m%d%H%M%S}-{secrets.token_hex(2).upper()}"
    try:
        o, _ = await osvc.create_order(
            db, r, external_id=ext, customer_name=body.customer_name.strip(), customer_phone=body.customer_phone.strip(),
            address=body.address.strip(), district=body.district.strip(), lat=body.lat, lng=body.lng, items=items,
            pay_method="Naqd", note=(body.note or "").strip() or None, delivery_fee=body.delivery_fee)
    except OrderError as e:
        raise ApiError(e.status, e.message)
    o.courier_note = (body.courier_note or "").strip() or None
    await log(db, o, u, "Buyurtma operator tomonidan yaratildi (naqd)")
    await commit(db)
    return await op_detail(db, o)


@router.get("/orders/{oid}")
async def get_order(oid: int, u: User = Depends(ops_user), db: AsyncSession = Depends(get_db)):
    return await op_detail(db, await load_order(db, oid))


@router.get("/orders/{oid}/route")
async def order_route(oid: int, u: User = Depends(ops_user), db: AsyncSession = Depends(get_db)):
    """Xarita uchun yo'l: kuryer -> restoran -> mijoz (yoki restoran -> mijoz)."""
    o = await load_order(db, oid)
    r = await db.get(Restaurant, o.restaurant_id)
    c = await db.get(Courier, o.courier_id) if o.courier_id else None
    if o.lat is None or o.lng is None:
        return {"legs": [], "distance_m": 0, "duration_s": 0, "approx": False}
    rest_pt = (o.handoff_lat, o.handoff_lng) if (o.handoff_lat is not None and o.status == "assigned") else (r.lat, r.lng)
    cust = (o.lat, o.lng)
    live_c = c is not None and c.lat is not None and not o.queued and o.status in ("assigned", "onway")
    pts: list[tuple[str, tuple[float, float]]] = []
    start = (r.lat, r.lng)
    if live_c and o.status == "onway":
        start = (c.lat, c.lng)
    elif live_c:
        start = (c.lat, c.lng)
        pts.append(("restaurant", rest_pt))
    pts.append(("customer", cust))
    speed = TRANSPORTS.get(c.vehicle if c else "Skuter", TRANSPORTS["Skuter"])["speed"]
    legs, cur = [], start
    for to, p in pts:
        g = await routing.leg(cur, p)
        legs.append({"to": to, **g, "duration_s": round(g["distance_m"] / 1000 / speed * 3600)})
        cur = p
    return {"legs": legs, "distance_m": sum(g["distance_m"] for g in legs), "duration_s": sum(g["duration_s"] for g in legs),
            "approx": any(g["approx"] for g in legs)}


# ---------------- Amallar ----------------
@router.post("/orders/{oid}/advance")
async def advance(oid: int, u: User = Depends(ops_user), db: AsyncSession = Depends(get_db)):
    """Keyingi bosqichga o'tkazish (to'lovni tasdiqlash / kuryer oldi / yetkazildi)."""
    o = await load_order(db, oid)
    act = next_action(o)
    if not act or act["kind"] == "assign":
        raise ApiError(409, "Bu bosqichda avval kuryer biriktirilishi kerak" if act else "Keyingi bosqich yo'q")
    c = await db.get(Courier, o.courier_id) if o.courier_id else None
    try:
        if act["kind"] == "confirm_payment":
            await set_payment(db, o, "paid")
            text = "To'lov tasdiqlandi"
        elif act["kind"] == "picked":
            await dispatch.picked_up(db, o, c)
            text = "Buyurtma \"Yo'lda\" bosqichiga o'tkazildi"
        else:
            await dispatch.delivered(db, o, c)
            text = "Buyurtma \"Yetkazildi\" deb belgilandi"
    except OrderError as e:
        raise ApiError(e.status, e.message)
    await log(db, o, u, text)
    await commit(db)
    return await op_detail(db, o)


@router.get("/orders/{oid}/couriers")
async def candidates(oid: int, q: str | None = None, u: User = Depends(ops_user), db: AsyncSession = Depends(get_db)):
    o = await load_order(db, oid)
    r = await db.get(Restaurant, o.restaurant_id)
    px, py = (o.handoff_lat, o.handoff_lng) if o.handoff_lat is not None else (r.lat, r.lng)
    stmt = select(Courier).where(Courier.account_status == "active", Courier.work_status != "offline")
    if o.courier_id:
        stmt = stmt.where(Courier.id != o.courier_id)
    if q and q.strip():
        s = q.strip()
        like = f"%{s}%"
        conds = [Courier.first_name.ilike(like), Courier.last_name.ilike(like),
                 (Courier.first_name + " " + Courier.last_name).ilike(like), Courier.phone.ilike(like)]
        if s.lstrip("#").isdigit():
            conds += [Courier.id == int(s.lstrip("#")), Courier.number == int(s.lstrip("#"))]
        stmt = stmt.where(or_(*conds))
    out = []
    for c in (await db.execute(stmt)).scalars():
        km = haversine(c.lat, c.lng, px, py) * ROAD_FACTOR if c.lat is not None else None
        speed = TRANSPORTS.get(c.vehicle, TRANSPORTS["Skuter"])["speed"]
        lab, tone = {"idle": ("bo'sh", "teal"), "pickup": ("band", "blue"), "delivering": ("band", "blue"),
                     "break": ("tanaffusda", "grey")}.get(c.work_status, (c.work_status, "grey"))
        out.append({"id": c.id, "number": c.number, "name": full_name(c), "phone": c.phone, "vehicle": c.vehicle,
                    "avatar_seed": c.avatar_seed, "is_female": c.is_female, "work_status": c.work_status,
                    "status_label": lab, "status_tone": tone, "balance": c.balance,
                    "over_limit": c.balance < -settings.CASH_LIMIT, "dist_km": round(km, 1) if km is not None else None,
                    "eta_min": max(1, round(km / speed * 60)) if km is not None else None,
                    "busy": c.current_order_id is not None, "selectable": c.work_status != "break"})
    out.sort(key=lambda x: (x["work_status"] != "idle", x["dist_km"] is None, x["dist_km"] or 0))
    return out[:60]


async def _detach_courier(db, o: Order, prev: Courier):
    """Buyurtmani joriy kuryeridan ajratish (kuryer bo'shaydi yoki navbatdagisini oladi)."""
    was_current = prev.current_order_id == o.id
    o.courier_id, o.queued, o.queue_position = None, False, None
    if was_current:
        await dispatch.finish_current(db, prev)
    else:
        await courier_changed(db, prev)


async def _expire_offers(db, o: Order):
    for of in (await db.execute(select(OrderOffer).where(OrderOffer.order_id == o.id, OrderOffer.result == "pending"))).scalars():
        of.result = "expired"


@router.post("/orders/{oid}/assign")
async def assign(oid: int, body: AssignIn, u: User = Depends(ops_user), db: AsyncSession = Depends(get_db)):
    o = await load_order(db, oid)
    if o.status not in ACTIVE:
        raise ApiError(409, "Yakunlangan buyurtmaga kuryer biriktirib bo'lmaydi")
    c = await db.get(Courier, body.courier_id)
    if not c or c.account_status != "active":
        raise ApiError(404, "Kuryer topilmadi yoki bloklangan")
    if c.id == o.courier_id:
        raise ApiError(409, "Bu kuryer allaqachon biriktirilgan")
    if c.work_status in ("offline", "break"):
        raise ApiError(409, "Kuryer hozir liniyada emas")
    prev = await db.get(Courier, o.courier_id) if o.courier_id else None
    await _expire_offers(db, o)
    if prev:
        if o.status == "onway" and prev.lat is not None:
            o.handoff_lat, o.handoff_lng = prev.lat, prev.lng
            o.handoff_name = f"Kuryer #{prev.number} qolgan joy"
        await _detach_courier(db, o, prev)
        o.reassigned_count = (o.reassigned_count or 0) + 1
    o.picked_at = None
    busy = c.current_order_id is not None and c.current_order_id != o.id
    if busy:
        qlen = (await db.execute(select(func.count()).select_from(Order).where(
            Order.courier_id == c.id, Order.queued.is_(True), Order.status == "assigned"))).scalar_one()
        await dispatch.queue_to_courier(db, o, c, qlen + 1)
    else:
        await dispatch.assign_to_courier(db, o, c)
    await log(db, o, u, f"Kuryer qo'lda {'almashtirildi' if prev else 'biriktirildi'}: {full_name(c)}"
                        + (f" (oldingi: {full_name(prev)})" if prev else "") + (" · navbatga qo'yildi" if busy else ""))
    await commit(db)
    return await op_detail(db, o)


@router.post("/orders/{oid}/unassign")
async def unassign(oid: int, u: User = Depends(ops_user), db: AsyncSession = Depends(get_db)):
    o = await load_order(db, oid)
    if o.status not in ("assigned", "onway") or not o.courier_id:
        raise ApiError(409, "Buyurtmada kuryer yo'q")
    prev = await db.get(Courier, o.courier_id)
    now = now_utc()
    if o.status == "onway" and prev.lat is not None:
        o.handoff_lat, o.handoff_lng = prev.lat, prev.lng
        o.handoff_name = f"Kuryer #{prev.number} qolgan joy"
    await _expire_offers(db, o)
    await _detach_courier(db, o, prev)
    o.status, o.assigned_at, o.picked_at, o.search_started_at = "new", None, None, now
    o.declined_courier_ids = list(o.declined_courier_ids or []) + [prev.id]
    o.reassigned_count = (o.reassigned_count or 0) + 1
    await feed(db, f"Operator <b>#{o.id}</b> ni {esc(full_name(prev))} dan olib tashladi", "amber", o.restaurant_id)
    await order_changed(db, o, status_changed=True)
    await log(db, o, u, f"Kuryer olib tashlandi: {full_name(prev)} · buyurtma qayta qidiruvga qo'yildi")
    await commit(db)
    return await op_detail(db, o)


@router.patch("/orders/{oid}/notes")
async def set_notes(oid: int, body: OrderNotesIn, u: User = Depends(ops_user), db: AsyncSession = Depends(get_db)):
    o = await load_order(db, oid)
    if o.status not in ACTIVE:
        raise ApiError(409, "Yakunlangan buyurtma izohini o'zgartirib bo'lmaydi")
    if body.restaurant_note is not None:
        o.note = body.restaurant_note.strip() or None
        await log(db, o, u, "Restoranga izoh o'zgartirildi")
    if body.courier_note is not None:
        o.courier_note = body.courier_note.strip() or None
        await log(db, o, u, "Kuryerga izoh o'zgartirildi")
    await order_changed(db, o)
    await commit(db)
    return await op_detail(db, o)


@router.post("/orders/{oid}/customer-notes", status_code=201)
async def add_customer_note(oid: int, body: CustomerNoteIn, u: User = Depends(ops_user), db: AsyncSession = Depends(get_db)):
    o = await load_order(db, oid)
    db.add(CustomerNote(phone=o.customer_phone, text=body.text.strip(), author=u.full_name or u.email))
    await log(db, o, u, f"Mijoz haqida eslatma qo'shildi: {body.text.strip()[:120]}")
    await commit(db)
    return await op_detail(db, o)


@router.post("/orders/{oid}/block-customer")
async def block_customer(oid: int, body: BlockIn, u: User = Depends(ops_user), db: AsyncSession = Depends(get_db)):
    o = await load_order(db, oid)
    if await db.get(BlockedCustomer, o.customer_phone):
        raise ApiError(409, "Mijoz allaqachon bloklangan")
    db.add(BlockedCustomer(phone=o.customer_phone, reason=body.reason.strip(), blocked_by=u.full_name or u.email))
    await log(db, o, u, "Mijoz bloklandi" + (f": {body.reason.strip()}" if body.reason.strip() else ""))
    await commit(db)
    return await op_detail(db, o)


@router.post("/orders/{oid}/unblock-customer")
async def unblock_customer(oid: int, u: User = Depends(ops_user), db: AsyncSession = Depends(get_db)):
    o = await load_order(db, oid)
    b = await db.get(BlockedCustomer, o.customer_phone)
    if not b:
        raise ApiError(409, "Mijoz bloklanmagan")
    await db.delete(b)
    await log(db, o, u, "Mijoz blokdan chiqarildi")
    await commit(db)
    return await op_detail(db, o)
