"""Kuryer klienti va restoranlarni taqlid qiluvchi demo simulyator (DEMO_SIMULATION=true)."""
import asyncio
import logging
import random
import time

from sqlalchemy import func, select

from app.config import ISSUES, TRANSPORTS
from app.db import SessionLocal
from app.menus import CUSTOMER_NAMES, DISTRICTS, pick_items, rand_phone
from app.models import Courier, Order, OrderIssue, OrderOffer, Restaurant
from app.services import dispatch
from app.services.events import commit, esc, feed
from app.services.geo import haversine
from app.services.live import courier_changed
from app.services.orders import OrderError, create_order, set_payment
from app.services.serializers import full_name, now_utc

log = logging.getLogger("yolda.sim")
SPEEDUP = 4.0          # demo uchun harakat tezlashtirilgan (haqiqiy tezlik * SPEEDUP)
PICKUP_DWELL = 6       # restoranda kutish, sekund
RESOLVE_PROB = {"noanswer": 0.6, "address": 0.5, "restdelay": 0.85, "wrong": 0.3, "vehicle": 0.0}
PAY_WEIGHTS = [("Payme", 32), ("Naqd", 28), ("Click", 20), ("Karta", 20)]


class Simulator:
    def __init__(self):
        t = time.monotonic()
        self.offer_plan: dict[int, tuple[float, bool]] = {}
        self.pending_pay: dict[int, tuple[float, bool]] = {}
        self.issue_plan: dict[int, float] = {}
        self.arrived: dict[int, float] = {}
        self.next_order = t + random.uniform(4, 8)
        self.next_issue = t + random.uniform(35, 60)
        self.counter = 0
        self.last = t

    async def tick(self, db):
        now = time.monotonic()
        dt = max(0.2, min(3.0, now - self.last))
        self.last = now
        await self.move(db, now, dt)
        await self.offers(db, now)
        await self.payments(db, now)
        await self.new_order(db, now)
        await self.issues(db, now)
        await self.breaks(db)
        await commit(db)

    async def move(self, db, now, dt):
        cs = (await db.execute(select(Courier).where(Courier.work_status.in_(("pickup", "delivering")),
                                                     Courier.current_order_id.is_not(None)))).scalars().all()
        open_issue = set((await db.execute(select(OrderIssue.order_id).where(OrderIssue.ended_at.is_(None)))).scalars())
        for c in cs:
            o = await db.get(Order, c.current_order_id)
            if o is None or c.lat is None or o.id in open_issue:
                continue
            r = await db.get(Restaurant, o.restaurant_id)
            speed = TRANSPORTS[c.vehicle]["speed"] * SPEEDUP
            step = speed / 3600 * dt
            if o.status == "assigned":
                tgt = (o.handoff_lat, o.handoff_lng) if o.handoff_lat is not None else (r.lat, r.lng)
            else:
                tgt = (o.lat, o.lng) if o.lat is not None else None
            if tgt is None:
                if o.picked_at and (now_utc() - o.picked_at).total_seconds() > 25:
                    await dispatch.delivered(db, o, c)
                continue
            d = haversine(c.lat, c.lng, *tgt)
            if d <= max(step, 0.03):
                c.lat, c.lng = tgt
                c.location_updated_at = now_utc()
                if o.status == "assigned":
                    t0 = self.arrived.setdefault(o.id, now)
                    if now - t0 >= PICKUP_DWELL:
                        self.arrived.pop(o.id, None)
                        await dispatch.picked_up(db, o, c)
                        continue
                else:
                    await dispatch.delivered(db, o, c)
                    continue
            else:
                f = step / d
                c.lat += (tgt[0] - c.lat) * f
                c.lng += (tgt[1] - c.lng) * f
                c.location_updated_at = now_utc()
            await courier_changed(db, c)

    async def offers(self, db, now):
        ofs = (await db.execute(select(OrderOffer).where(OrderOffer.result == "pending",
                                                         OrderOffer.expires_at > now_utc()))).scalars().all()
        for of in ofs:
            plan = self.offer_plan.get(of.id)
            if plan is None:
                self.offer_plan[of.id] = (now + random.uniform(4, 10), random.random() < 0.85)
                continue
            if now < plan[0]:
                continue
            c = await db.get(Courier, of.courier_id)
            try:
                if plan[1]:
                    await dispatch.accept_offer(db, of, c)
                else:
                    await dispatch.decline_offer(db, of, c)
            except OrderError:
                pass
            self.offer_plan.pop(of.id, None)

    async def payments(self, db, now):
        for oid, (at, ok) in list(self.pending_pay.items()):
            if now < at:
                continue
            self.pending_pay.pop(oid)
            o = await db.get(Order, oid)
            if o and o.pay_status == "pending" and o.status == "new":
                try:
                    await set_payment(db, o, "paid" if ok else "failed")
                except OrderError:
                    pass

    async def new_order(self, db, now):
        if now < self.next_order:
            return
        self.next_order = now + random.uniform(16, 26)
        rests = (await db.execute(select(Restaurant).where(Restaurant.status == "open"))).scalars().all()
        if not rests:
            return
        r = random.choice(rests)
        rnd = random
        dname = rnd.choice(list(DISTRICTS))
        la, ln = DISTRICTS[dname]
        lat, lng = la + rnd.uniform(-0.02, 0.02), ln + rnd.uniform(-0.02, 0.02)
        method = rnd.choices([m for m, _ in PAY_WEIGHTS], [w for _, w in PAY_WEIGHTS])[0]
        pending = method != "Naqd" and rnd.random() < 0.25
        self.counter += 1
        ext = f"SIM-{int(time.time())}-{self.counter}"
        try:
            o, created = await create_order(
                db, r, external_id=ext, customer_name=rnd.choice(CUSTOMER_NAMES), customer_phone=rand_phone(rnd),
                address=f"{dname}, {rnd.randint(1, 60)}-uy", district=dname, lat=lat, lng=lng,
                items=pick_items(r, rnd), pay_method=method, pay_status="pending" if pending else "paid")
        except OrderError:
            return
        if pending:
            await db.flush()
            self.pending_pay[o.id] = (now + rnd.uniform(6, 15), rnd.random() < 0.8)

    async def issues(self, db, now):
        # avtomatik hal bo'lish
        opened = (await db.execute(select(OrderIssue).where(OrderIssue.ended_at.is_(None)))).scalars().all()
        for i in opened:
            at = self.issue_plan.setdefault(i.id, now + random.uniform(25, 70))
            if now < at or i.kind == "vehicle":
                continue
            if random.random() < RESOLVE_PROB[i.kind]:
                o = await db.get(Order, i.order_id)
                try:
                    await dispatch.resolve_issue(db, o, "tizim (avtomatik)")
                except OrderError:
                    pass
                self.issue_plan.pop(i.id, None)
            else:
                self.issue_plan[i.id] = now + 30
        if now < self.next_issue or len(opened) >= 3:
            return
        self.next_issue = now + random.uniform(35, 60)
        busy_orders = {i.order_id for i in opened}
        cs = (await db.execute(select(Courier).where(Courier.work_status.in_(("pickup", "delivering")),
                                                     Courier.current_order_id.is_not(None)))).scalars().all()
        cs = [c for c in cs if c.current_order_id not in busy_orders]
        if not cs:
            return
        c = random.choice(cs)
        kinds = ["restdelay", "restdelay", "vehicle"] if c.work_status == "pickup" else \
            ["noanswer", "noanswer", "address", "wrong", "vehicle"]
        try:
            await dispatch.open_issue(db, c, random.choice(kinds))
        except OrderError:
            pass

    async def breaks(self, db):
        now = now_utc()
        for c in (await db.execute(select(Courier).where(Courier.work_status == "break",
                                                         Courier.break_until <= now))).scalars().all():
            c.work_status, c.break_until, c.idle_since = "idle", None, now
            await feed(db, f"<b>{esc(full_name(c))} #{c.number}</b> tanaffusdan qaytdi", "amber")
            await courier_changed(db, c)


async def simulator_loop():
    sim = Simulator()
    while True:
        try:
            async with SessionLocal() as db:
                await sim.tick(db)
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("simulyator xatosi")
        await asyncio.sleep(1)
