"""Dashbordda onlayn to'lovlar ro'yxati (barcha ulangan restoranlar uchun yagona Multicard kassasi)."""
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import ops_user
from app.errors import ApiError
from app.models import Payment, Restaurant, User
from app.services import payments as psvc
from app.services import stats
from app.services.events import commit
from app.services.serializers import iso

router = APIRouter(prefix="/payments", tags=["payments"])

STATUS_LABELS = {"pending": "Kutilmoqda", "paid": "To'langan", "cancelled": "Bekor qilingan", "expired": "Muddati o'tgan",
                 "refund_required": "Qaytarish kerak", "refunded": "Qaytarilgan"}


def _row(p: Payment, rname: str) -> dict:
    return {"id": p.id, "order_id": p.order_id, "restaurant": {"id": p.restaurant_id, "name": rname}, "method": p.method,
            "ps": p.ps, "card": p.card_pan, "amount": p.amount, "status": p.status, "status_label": STATUS_LABELS.get(p.status, p.status),
            "invoice_id": p.invoice_id, "provider_uuid": p.provider_uuid, "pay_url": p.checkout_url, "receipt_url": p.receipt_url,
            "created_at": iso(p.created_at), "paid_at": iso(p.paid_at), "expires_at": iso(p.expires_at)}


@router.get("")
async def list_payments(status: str | None = None, method: str | None = None, restaurant_id: int | None = None,
                        q: str | None = None, from_: date | None = Query(None, alias="from"), to: date | None = None,
                        page: int = Query(1, ge=1), per_page: int = Query(20, ge=1, le=100),
                        u: User = Depends(ops_user), db: AsyncSession = Depends(get_db)):
    base = select(Payment, Restaurant.name).join(Restaurant, Restaurant.id == Payment.restaurant_id)
    if status:
        base = base.where(Payment.status == status)
    if method:
        base = base.where(Payment.method == method)
    if restaurant_id:
        base = base.where(Payment.restaurant_id == restaurant_id)
    if q and q.strip():
        t = q.strip()
        base = base.where(Payment.invoice_id.ilike(f"%{t}%") | (Payment.order_id == int(t) if t.isdigit() else False))
    if from_:
        base = base.where(Payment.created_at >= stats.day_start(from_))
    if to:
        base = base.where(Payment.created_at < stats.day_start(to + timedelta(days=1)))
    sub = base.subquery()
    total = (await db.execute(select(func.count()).select_from(sub))).scalar_one()
    sums = (await db.execute(select(sub.c.status, func.count(), func.coalesce(func.sum(sub.c.amount), 0)).group_by(sub.c.status))).all()
    by = {s: {"count": c, "amount": int(a)} for s, c, a in sums}
    rows = (await db.execute(base.order_by(Payment.id.desc()).offset((page - 1) * per_page).limit(per_page))).all()
    rests = (await db.execute(select(Restaurant.id, Restaurant.name).order_by(Restaurant.name))).all()
    return {"items": [_row(p, n) for p, n in rows], "total": total, "by_status": by,
            "summary": {"paid": by.get("paid", {"count": 0, "amount": 0}), "refund_required": by.get("refund_required", {"count": 0, "amount": 0})},
            "statuses": [{"value": k, "label": v} for k, v in STATUS_LABELS.items()],
            "methods": [{"value": m["code"], "label": m["name"]} for m in psvc.enabled_methods()],
            "restaurants": [{"value": i, "label": n} for i, n in rests]}


async def _load(db, pid: int) -> tuple[Payment, str]:
    p = await db.get(Payment, pid)
    if not p:
        raise ApiError(404, "To'lov topilmadi")
    r = await db.get(Restaurant, p.restaurant_id)
    return p, r.name


@router.post("/{pid}/sync")
async def sync(pid: int, u: User = Depends(ops_user), db: AsyncSession = Depends(get_db)):
    """Multicard dan holatni qayta so'raydi (callback kelmagan bo'lsa)."""
    p, n = await _load(db, pid)
    try:
        await psvc.sync_payment(db, p)
    except psvc.PaymentError as e:
        await db.rollback()
        raise ApiError(e.status, e.message)
    await commit(db)
    return _row(p, n)


@router.post("/{pid}/refund")
async def refund(pid: int, u: User = Depends(ops_user), db: AsyncSession = Depends(get_db)):
    p, n = await _load(db, pid)
    try:
        await psvc.refund_payment(db, p)
    except psvc.PaymentError as e:
        await db.rollback()
        raise ApiError(e.status, e.message)
    await commit(db)
    return _row(p, n)
