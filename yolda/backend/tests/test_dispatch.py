from datetime import timedelta
from types import SimpleNamespace

from sqlalchemy import select

from app.models import LedgerEntry, Order, OrderOffer
from app.services import dispatch
from app.services.orders import create_order
from app.services.serializers import now_utc
from tests.conftest import make_courier, make_restaurant


def _courier(**kw):
    d = dict(account_status="active", work_status="idle", vehicle="Skuter", balance=0, lat=1.0, lng=1.0)
    d.update(kw)
    return SimpleNamespace(**d)


def _order(**kw):
    d = dict(distance_km=3.0, pay_method="Payme")
    d.update(kw)
    return SimpleNamespace(**d)


def test_can_take_rules():
    assert dispatch.can_take(_courier(), _order(), False)
    assert not dispatch.can_take(_courier(account_status="blocked"), _order(), False)
    assert not dispatch.can_take(_courier(work_status="offline"), _order(), False)
    assert not dispatch.can_take(_courier(work_status="break"), _order(), False)
    assert not dispatch.can_take(_courier(), _order(), True)                      # ochiq muammo
    assert not dispatch.can_take(_courier(vehicle="Piyoda"), _order(distance_km=2.6), False)
    assert dispatch.can_take(_courier(vehicle="Piyoda"), _order(distance_km=2.5), False)
    assert not dispatch.can_take(_courier(vehicle="Velo"), _order(distance_km=5.1), False)
    assert not dispatch.can_take(_courier(vehicle="Skuter"), _order(distance_km=12.5), False)
    assert dispatch.can_take(_courier(vehicle="Avto"), _order(distance_km=80), False)
    # naqd: balans -400 000 dan past bo'lmasa
    assert dispatch.can_take(_courier(balance=-400_000), _order(pay_method="Naqd"), False)
    assert not dispatch.can_take(_courier(balance=-400_001), _order(pay_method="Naqd"), False)
    assert dispatch.can_take(_courier(balance=-900_000), _order(pay_method="Payme"), False)


def test_candidate_distance_busy_vs_idle():
    rest = SimpleNamespace(lat=41.30, lng=69.20)
    idle = _courier(lat=41.31, lng=69.20, current_order_id=None)
    busy = _courier(lat=41.31, lng=69.20, current_order_id=5)
    d_idle = dispatch.candidate_distance(idle, rest, None, 0)
    d_busy = dispatch.candidate_distance(busy, rest, (41.32, 69.21), 1)
    assert d_busy > d_idle + 5


async def _new_order(db, r, ext="A", method="Payme", status="paid", lat=41.37, lng=69.30):
    o, _ = await create_order(db, r, external_id=ext, customer_name="T", customer_phone="+998900000000", address="a",
                              lat=lat, lng=lng, items=[{"name": "x", "qty": 1, "price": 10000}],
                              pay_method=method, pay_status=status)
    await db.commit()
    return o


async def test_offer_goes_to_nearest_idle_and_skips_pending_payment(db):
    r = await make_restaurant(db)
    near = await make_courier(db, lat=41.361, lng=69.291)
    await make_courier(db, lat=41.40, lng=69.35)
    await make_courier(db, lat=41.361, lng=69.291, status="break")
    pend = await _new_order(db, r, "P", status="pending")
    await dispatch.dispatch_cycle(db)
    await db.commit()
    assert (await db.execute(select(OrderOffer))).first() is None            # pending to'lov: taklif yo'q
    pend.pay_status = "paid"
    await db.commit()
    await dispatch.dispatch_cycle(db)
    await db.commit()
    of = (await db.execute(select(OrderOffer))).scalars().one()
    assert of.courier_id == near.id and of.result == "pending"
    assert 25 <= (of.expires_at - now_utc()).total_seconds() <= 30


async def test_decline_expire_and_cash_limit(db):
    r = await make_restaurant(db)
    c1 = await make_courier(db, lat=41.361, lng=69.291, balance=-500_000)   # naqd limiti oshgan
    c2 = await make_courier(db, lat=41.37, lng=69.30)
    o = await _new_order(db, r, "N", method="Naqd")
    await dispatch.dispatch_cycle(db)
    await db.commit()
    of = (await db.execute(select(OrderOffer))).scalars().one()
    assert of.courier_id == c2.id                                              # c1 ga naqd berilmaydi
    await dispatch.decline_offer(db, of, c2)
    await db.commit()
    await db.refresh(o)
    assert o.declined_courier_ids == [c2.id]
    await dispatch.dispatch_cycle(db)
    await db.commit()
    assert len((await db.execute(select(OrderOffer))).scalars().all()) == 1    # boshqa nomzod yo'q
    # muddat o'tishi -> expired va declined
    o.declined_courier_ids = []
    await db.commit()
    await dispatch.dispatch_cycle(db)
    await db.commit()
    of2 = (await db.execute(select(OrderOffer).order_by(OrderOffer.id.desc()))).scalars().first()
    of2.expires_at = now_utc() - timedelta(seconds=1)
    await db.commit()
    await dispatch.dispatch_cycle(db)
    await db.commit()
    await db.refresh(of2)
    assert of2.result == "expired"


async def test_full_flow_ledger_and_queue(db):
    r = await make_restaurant(db)
    c = await make_courier(db, lat=41.361, lng=69.291)
    o = await _new_order(db, r, "F", method="Naqd")
    await dispatch.dispatch_cycle(db)
    await db.commit()
    of = (await db.execute(select(OrderOffer))).scalars().one()
    await dispatch.accept_offer(db, of, c)
    await db.commit()
    await db.refresh(o)
    await db.refresh(c)
    assert o.status == "assigned" and c.current_order_id == o.id and c.work_status == "pickup"
    # band kuryerga navbat: 60 soniyadan keyin
    o2 = await _new_order(db, r, "F2")
    o2.search_started_at = now_utc() - timedelta(seconds=61)
    await db.commit()
    await dispatch.dispatch_cycle(db)
    await db.commit()
    await db.refresh(o2)
    assert o2.queued and o2.courier_id == c.id and o2.status == "assigned"
    await dispatch.picked_up(db, o, c)
    await dispatch.delivered(db, o, c)
    await db.commit()
    await db.refresh(c)
    await db.refresh(o)
    await db.refresh(o2)
    assert o.status == "delivered" and o.pay_status == "collected"
    assert c.current_order_id == o2.id and not o2.queued                       # navbatdagi avtomatik olindi
    entries = (await db.execute(select(LedgerEntry).where(LedgerEntry.courier_id == c.id))).scalars().all()
    assert {e.type for e in entries} == {"earn", "cash"}
    assert c.balance == sum(e.amount for e in entries)
    assert next(e for e in entries if e.type == "cash").amount == -o.total


async def test_vehicle_issue_auto_reassign(db):
    r = await make_restaurant(db)
    c = await make_courier(db, lat=41.361, lng=69.291)
    o = await _new_order(db, r, "V")
    await dispatch.dispatch_cycle(db)
    await db.commit()
    of = (await db.execute(select(OrderOffer))).scalars().one()
    await dispatch.accept_offer(db, of, c)
    await dispatch.picked_up(db, o, c)
    await db.commit()
    i = await dispatch.open_issue(db, c, "vehicle")
    i.auto_at = now_utc() - timedelta(seconds=1)
    await db.commit()
    await dispatch.auto_reassign_vehicle(db)
    await db.commit()
    await db.refresh(o)
    await db.refresh(c)
    assert o.status == "new" and o.courier_id is None and o.declined_courier_ids == [c.id]
    assert o.reassigned_count == 1 and o.handoff_lat == c.lat
    assert c.work_status == "offline" and c.current_order_id is None
