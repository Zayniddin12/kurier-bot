"""Moliya: kuryer (haydovchi) va vendor (restoran) tranzaksiyalari."""
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import LEDGER_TYPES, VENDOR_LEDGER_TYPES
from app.db import get_db
from app.deps import ops_user
from app.models import Courier, LedgerEntry, Restaurant, User, VendorLedgerEntry
from app.services import stats
from app.services.serializers import full_name, iso

router = APIRouter(prefix="/finance", tags=["finance"])


def _range(q, col, from_: date | None, to_: date | None):
    if from_:
        q = q.where(col >= stats.day_start(from_))
    if to_:
        q = q.where(col < stats.day_start(to_ + timedelta(days=1)))
    return q


def _desc(note: str | None, order_id: int | None) -> str:
    n = (note or "").rstrip(".")
    return f"{n}. Buyurtma raqami: {order_id}" if order_id else n


async def _summary(db, q_filtered) -> dict:
    sub = q_filtered.subquery()
    inc, exp = (await db.execute(select(
        func.coalesce(func.sum(case((sub.c.amount > 0, sub.c.amount), else_=0)), 0),
        func.coalesce(func.sum(case((sub.c.amount < 0, -sub.c.amount), else_=0)), 0)))).one()
    return {"income": int(inc), "expense": int(exp), "balance": int(inc) - int(exp)}


@router.get("/couriers")
async def courier_transactions(courier_id: int | None = None, q: str | None = None, pinfl: str | None = None,
                               desc: str | None = None, kind: str | None = None, reason: str | None = None,
                               from_: date | None = Query(None, alias="from"), to: date | None = None,
                               page: int = Query(1, ge=1), per_page: int = Query(20, ge=1, le=200),
                               u: User = Depends(ops_user), db: AsyncSession = Depends(get_db)):
    E = LedgerEntry
    run = func.sum(E.amount).over(partition_by=E.courier_id, order_by=(E.created_at, E.id)).label("balance_after")
    base = select(E.id, E.courier_id, E.type, E.amount, E.order_id, E.note, E.created_at, run).subquery("e")
    stmt = (select(base, Courier).join(Courier, Courier.id == base.c.courier_id))
    if courier_id is not None:
        stmt = stmt.where((Courier.id == courier_id) | (Courier.number == courier_id))
    if q:
        stmt = stmt.where((Courier.first_name + " " + Courier.last_name).ilike(f"%{q.strip()}%")
                          | (Courier.last_name + " " + Courier.first_name).ilike(f"%{q.strip()}%"))
    if pinfl:
        stmt = stmt.where(Courier.pinfl.contains(pinfl.strip()))
    if desc:
        stmt = stmt.where(base.c.note.ilike(f"%{desc.strip()}%"))
    if kind == "income":
        stmt = stmt.where(base.c.amount > 0)
    elif kind == "expense":
        stmt = stmt.where(base.c.amount < 0)
    if reason:
        stmt = stmt.where(base.c.type == reason)
    stmt = _range(stmt, base.c.created_at, from_, to)

    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    summ = await _summary(db, select(stmt.subquery().c.amount))
    rows = (await db.execute(stmt.order_by(base.c.created_at.desc(), base.c.id.desc())
                             .limit(per_page).offset((page - 1) * per_page))).all()
    items = []
    for r in rows:
        c = r[-1]
        lab, color = LEDGER_TYPES[r.type]
        items.append({"id": r.id, "courier": {"id": c.id, "number": c.number, "name": full_name(c)}, "pinfl": c.pinfl,
                      "kind": "income" if r.amount > 0 else "expense", "amount": r.amount, "reason": r.type,
                      "reason_label": lab, "description": _desc(r.note, r.order_id), "order_id": r.order_id,
                      "created_at": iso(r.created_at), "balance_after": int(r.balance_after)})
    return {"items": items, "total": total, "summary": summ,
            "reasons": [{"value": k, "label": v[0]} for k, v in LEDGER_TYPES.items()]}


@router.get("/vendors")
async def vendor_transactions(restaurant_id: int | None = None, q: str | None = None, desc: str | None = None,
                              kind: str | None = None, type: str | None = None, creator: str | None = None,
                              from_: date | None = Query(None, alias="from"), to: date | None = None,
                              page: int = Query(1, ge=1), per_page: int = Query(20, ge=1, le=200),
                              u: User = Depends(ops_user), db: AsyncSession = Depends(get_db)):
    E = VendorLedgerEntry
    run = func.sum(E.amount).over(partition_by=E.restaurant_id, order_by=(E.created_at, E.id)).label("balance_after")
    base = select(E.id, E.restaurant_id, E.type, E.amount, E.order_id, E.note, E.created_by, E.created_at, run).subquery("e")
    stmt = select(base, Restaurant.name.label("rname"), Restaurant.color.label("rcolor"),
                  User.full_name.label("uname")).join(Restaurant, Restaurant.id == base.c.restaurant_id)\
        .outerjoin(User, User.id == base.c.created_by)
    if restaurant_id is not None:
        stmt = stmt.where(Restaurant.id == restaurant_id)
    if q:
        stmt = stmt.where(Restaurant.name.ilike(f"%{q.strip()}%"))
    if desc:
        stmt = stmt.where(base.c.note.ilike(f"%{desc.strip()}%"))
    if kind == "income":
        stmt = stmt.where(base.c.amount > 0)
    elif kind == "expense":
        stmt = stmt.where(base.c.amount < 0)
    if type:
        stmt = stmt.where(base.c.type == type)
    if creator == "system":
        stmt = stmt.where(base.c.created_by.is_(None))
    elif creator and creator.isdigit():
        stmt = stmt.where(base.c.created_by == int(creator))
    stmt = _range(stmt, base.c.created_at, from_, to)

    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    summ = await _summary(db, select(stmt.subquery().c.amount))
    rows = (await db.execute(stmt.order_by(base.c.created_at.desc(), base.c.id.desc())
                             .limit(per_page).offset((page - 1) * per_page))).all()
    items = []
    for r in rows:
        lab, color = VENDOR_LEDGER_TYPES.get(r.type, (r.type, "grey"))
        items.append({"id": r.id, "restaurant": {"id": r.restaurant_id, "name": r.rname, "color": r.rcolor},
                      "kind": "income" if r.amount > 0 else "expense", "amount": r.amount, "type": r.type,
                      "type_label": lab, "type_color": color, "creator": r.uname or "Tizim",
                      "description": _desc(r.note, r.order_id), "order_id": r.order_id,
                      "created_at": iso(r.created_at), "balance_after": int(r.balance_after)})
    creators = (await db.execute(select(User.id, User.full_name).where(
        User.id.in_(select(E.created_by).where(E.created_by.is_not(None)).distinct())))).all()
    return {"items": items, "total": total, "summary": summ,
            "types": [{"value": k, "label": v[0]} for k, v in VENDOR_LEDGER_TYPES.items()],
            "creators": [{"value": "system", "label": "Tizim"}] + [{"value": str(i), "label": n} for i, n in creators]}
