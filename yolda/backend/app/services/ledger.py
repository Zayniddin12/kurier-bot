"""Pul hisoblari va kuryer balansi (ledger). Barcha summalar so'mda (int)."""
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import Courier, LedgerEntry, Order


def _round_half_up(x: float) -> int:
    return int(x + 0.5) if x >= 0 else -int(-x + 0.5)


def delivery_fee_for(km: float) -> int:
    return _round_half_up((7000 + km * 1500) / 1000) * 1000


def courier_earning(delivery_fee: int) -> int:
    return _round_half_up(delivery_fee * (1 - settings.COMMISSION) / 100) * 100


def platform_commission(delivery_fee: int) -> int:
    return delivery_fee - courier_earning(delivery_fee)


def salary_math(balance: int, deliveries: int, late: int) -> dict:
    bonus = (deliveries // 10) * settings.BONUS_PER_10
    fine = late * settings.LATE_FINE
    return {"bonus": bonus, "fine": fine, "payable": max(0, balance + bonus - fine)}


async def add_entry(db: AsyncSession, courier: Courier, type_: str, amount: int, order_id: int | None = None,
                    note: str | None = None, created_by: int | None = None) -> LedgerEntry:
    """Yozuv qo'shish va balansni yangilash — bitta tranzaksiyada (commit chaqiruvchida)."""
    e = LedgerEntry(courier_id=courier.id, type=type_, amount=amount, order_id=order_id, note=note,
                    created_by=created_by, created_at=datetime.now(timezone.utc))
    db.add(e)
    courier.balance = (courier.balance or 0) + amount
    return e


async def settle_numbers(db: AsyncSession, courier: Courier) -> dict:
    q = select(func.count(), func.count().filter(Order.is_late.is_(True))).where(
        Order.courier_id == courier.id, Order.status == "delivered")
    if courier.settled_at:
        q = q.where(Order.delivered_at > courier.settled_at)
    n, late = (await db.execute(q)).one()
    # daromad = har bir buyurtma bo'yicha alohida yaxlitlangan
    fq = select(Order.delivery_fee).where(Order.courier_id == courier.id, Order.status == "delivered")
    if courier.settled_at:
        fq = fq.where(Order.delivered_at > courier.settled_at)
    earned = sum(courier_earning(f) for f in (await db.execute(fq)).scalars())
    r = salary_math(courier.balance, n, late)
    return {"deliveries": n, "earned": earned, "late": late, **r}


async def settle(db: AsyncSession, courier: Courier, user_id: int | None) -> int:
    s = await settle_numbers(db, courier)
    if s["bonus"] > 0:
        await add_entry(db, courier, "fix", s["bonus"], note=f"Bonus: {s['deliveries']} ta yetkazish", created_by=user_id)
    if s["fine"] > 0:
        await add_entry(db, courier, "penalty", -s["fine"], note=f"{s['late']} ta kechikish", created_by=user_id)
    if s["payable"] > 0:
        await add_entry(db, courier, "payout", -s["payable"], note="Maosh hisob-kitobi", created_by=user_id)
    courier.settled_at = datetime.now(timezone.utc)
    return s["payable"]
