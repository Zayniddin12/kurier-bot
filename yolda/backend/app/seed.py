"""Demo ma'lumotlar: python -m app.seed [--reset]"""
import asyncio
import math
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select, text

from app.config import settings
from app.db import SessionLocal, engine
from app.menus import (CANCEL_REASONS, CUSTOMER_NAMES, DISTRICTS, FIRST_NAMES, LAST_NAMES, MENUS, RESTAURANT_MENU,
                       menu_for, pick_items, rand_phone)
from app.models import (Complaint, Courier, FeedEvent, LedgerEntry, Order, OrderItem, Restaurant, User)
from app.security import hash_password, new_api_key
from app.services.geo import haversine, road_km
from app.services.ledger import courier_earning, delivery_fee_for
from app.services.stats import TZ

R = random.Random(42)
UTC = timezone.utc

RESTAURANTS = [
    # name, cuisine, district, address, color, type, pos, rating, prep, hours, manager, status, pause_reason, phone
    ("Mondi kafe", "Kafe, desertlar", "Yunusobod", "Amir Temur shoh ko'chasi, 108", "#E4572E", "API", "iiko", 4.8, 16, "08:00–23:00", "Lola Ahmedova", "open", None, "+998 71 200 10 01"),
    ("Rayhon milliy taomlar", "Milliy taomlar", "Shayxontohur", "Navoiy ko'chasi, 21", "#2E8B57", "POS", "R-Keeper", 4.7, 22, "09:00–23:00", "Akbar Yusupov", "open", None, "+998 71 200 10 02"),
    ("Lavash Markazi", "Fast-fud", "Chilonzor", "Bunyodkor shoh ko'chasi, 14", "#E8871E", "API", "Poster", 4.5, 12, "10:00–03:00", "Sherzod Aliyev", "open", None, "+998 71 200 10 03"),
    ("Pizza Bello", "Pitsa, italyan", "Mirobod", "Mirobod ko'chasi, 33", "#C0392B", "API", "iiko", 4.6, 20, "10:00–23:00", "Marco Rossi", "open", None, "+998 71 200 10 04"),
    ("Sakura Sushi", "Yapon oshxonasi", "Mirzo Ulug'bek", "Mirzo Ulug'bek ko'chasi, 77", "#8E44AD", "Planshet", "Yo'lda planshet", 4.9, 25, "11:00–23:00", "Kenji Sato", "open", None, "+998 71 200 10 05"),
    ("Choyxona Navro'z", "Osh, milliy taomlar", "Yakkasaroy", "Shota Rustaveli ko'chasi, 9", "#138A72", "POS", "R-Keeper", 4.7, 18, "08:00–23:00", "Hamid Karimov", "open", None, "+998 71 200 10 06"),
    ("Burger Town", "Burgerlar", "Yunusobod", "Amir Temur shoh ko'chasi, 150", "#C4511A", "API", "Poster", 4.4, 14, "10:00–02:00", "Dilshod Toshev", "open", None, "+998 71 200 10 07"),
    ("Shashlik Usta", "Grill, shashlik", "Olmazor", "Olmazor ko'chasi, 5", "#7F5539", "Planshet", "Yo'lda planshet", 4.6, 24, "11:00–00:00", "Ravshan Nurov", "open", None, "+998 71 200 10 08"),
    ("Green Bowl", "Sog'lom ovqat", "Mirobod", "Taras Shevchenko ko'chasi, 19", "#5E8C45", "API", "iiko", 4.8, 15, "09:00–22:00", "Nilufar Qosimova", "open", None, "+998 71 200 10 09"),
    ("Somsa Ota", "Somsa, non", "Yashnobod", "Yashnobod ko'chasi, 3", "#A85F1F", "Planshet", "Yo'lda planshet", 4.7, 10, "07:00–21:00", "Otabek Soliyev", "open", None, "+998 71 200 10 10"),
    ("Dolce Cafe", "Kofe, shirinliklar", "Yakkasaroy", "Bobur ko'chasi, 12", "#A5677A", "API", "Poster", 4.5, 12, "08:00–22:00", "Zarina Ismoilova", "open", None, "+998 71 200 10 11"),
    ("Sergeli Lavash", "Fast-fud", "Sergeli", "Sergeli ko'chasi, 40", "#C98A1E", "POS", "iiko", 4.2, 13, "10:00–01:00", "Baxrom Eshonov", "paused", "Oshxona jihozi ta'mirda", "+998 71 200 10 12"),
]
REST_W = [1.5, 1.0, 1.1, 1.0, 0.8, 1.0, 1.0, 0.9, 0.9, 0.9, 0.9, 0.0]
COEF = {6: 1.2, 0: 0.9, 1: 0.9, 2: 0.95, 3: 1.0, 4: 1.15, 5: 1.25}  # python weekday: Mon=0..Sun=6
HOUR_W = [0.2, 0.1, 0.1, 0.1, 0.1, 0.1, 0.2, 0.5, 1.0, 1.5, 2.5, 4, 6, 6, 4, 3, 3, 4, 6, 7, 7, 5, 2.5, 1]
PAYS = ["Payme", "Naqd", "Click", "Karta"]
PAY_W = [32, 28, 20, 20]
VEHICLES = ["Skuter"] * 13 + ["Avto"] * 8 + ["Velo"] * 3 + ["Piyoda"] * 2
STATES = ["delivering"] * 10 + ["pickup"] * 5 + ["idle"] * 7 + ["break"] * 2 + ["offline"] * 2


def rand_point(lat, lng, kmin, kmax):
    d = R.uniform(kmin, kmax)
    b = R.uniform(0, 2 * math.pi)
    return lat + d * math.cos(b) / 111.0, lng + d * math.sin(b) / (111.0 * math.cos(math.radians(lat)))


def max_km(vehicle):
    return {"Skuter": 12, "Avto": 40, "Velo": 5, "Piyoda": 2.5}[vehicle]


def fmt_plate():
    return f"{R.randint(1, 95):02d} {R.choice('ABCDEKMX')} {R.randint(100, 999)} {''.join(R.choice('ABCDEKMNPRSTX') for _ in range(2))}"


async def reset(db):
    await db.execute(text("TRUNCATE webhook_deliveries, dismissed_alerts, complaints, feed_events, ledger_entries, "
                          "order_issues, order_offers, order_items, orders, couriers, users, restaurants RESTART IDENTITY CASCADE"))
    await db.execute(text("ALTER SEQUENCE orders_id_seq RESTART WITH 118401"))
    await db.commit()


def build_order(r: Restaurant, created: datetime, pay_method: str, courier_max: float | None = None, kmax_extra=None):
    """Mijoz nuqtasi va narxlarni hisoblab Order obyektini yaratadi (status keyin qo'yiladi)."""
    cap = min(courier_max or 12, 9.0) / 1.25
    for _ in range(10):
        dname = R.choice(list(DISTRICTS))
        la, ln = DISTRICTS[dname]
        lat, lng = la + R.uniform(-0.02, 0.02), ln + R.uniform(-0.02, 0.02)
        if road_km(r.lat, r.lng, lat, lng) <= (courier_max or 12):
            break
    else:
        dname = r.district
        lat, lng = rand_point(r.lat, r.lng, 0.5, max(0.6, cap * 0.8))
    km = road_km(r.lat, r.lng, lat, lng)
    items = pick_items(r, R)
    sub = sum(i["qty"] * i["price"] for i in items)
    fee = delivery_fee_for(km)
    o = Order(restaurant_id=r.id, external_id=f"{r.name[:3].upper()}-{R.randint(10000, 99999)}-{R.randint(100, 999)}",
              created_at=created, status="new", subtotal=sub, delivery_fee=fee, total=sub + fee, distance_km=km,
              pay_method=pay_method, pay_status="cod" if pay_method == "Naqd" else "paid",
              customer_name=R.choice(CUSTOMER_NAMES), customer_phone=rand_phone(R), district=dname,
              address=f"{dname}, {R.randint(1, 80)}-uy, {R.randint(1, 120)}-xonadon", lat=lat, lng=lng,
              note=R.choice([None, None, None, "Domofon ishlamaydi, qo'ng'iroq qiling", "Eshik oldiga qoldiring"]),
              declined_courier_ids=[], prep_minutes=r.prep_minutes + R.randint(-3, 3), search_started_at=created)
    o._items = items  # type: ignore[attr-defined]
    return o


async def main(do_reset: bool):
    async with SessionLocal() as db:
        if do_reset:
            await reset(db)
        if (await db.execute(select(User.id).limit(1))).first():
            print("Seed allaqachon bajarilgan (qayta yaratish uchun: python -m app.seed --reset)")
            return
        now = datetime.now(UTC)
        local_now = now.astimezone(TZ)
        today0 = datetime.combine(local_now.date(), datetime.min.time(), tzinfo=TZ)

        # ---- restoranlar
        rests: list[Restaurant] = []
        mondi_key = None
        for i, t in enumerate(RESTAURANTS):
            name, cuisine, district, addr, color, itype, pos, rating, prep, hours, mgr, status, pr, phone = t
            la, ln = DISTRICTS[district]
            lat, lng = (41.3608, 69.2905) if i == 0 else (la + R.uniform(-0.008, 0.008), ln + R.uniform(-0.008, 0.008))
            key, prefix, h = new_api_key()
            if i == 0:
                mondi_key = key
            r = Restaurant(name=name, cuisine=cuisine, district=district, address=addr, lat=lat, lng=lng, color=color,
                           integration_type=itype, pos_system=pos, status=status, pause_reason=pr, rating=rating,
                           prep_minutes=prep, phone=phone, hours=hours, manager=mgr,
                           connected_at=now - timedelta(days=R.randint(60, 600)),
                           last_sync_at=now - timedelta(seconds=R.randint(3, 40) if status == "open" else 180),
                           api_key_prefix=prefix, api_key_hash=h)
            db.add(r)
            rests.append(r)
        await db.flush()
        open_rests = [r for r in rests if r.status == "open"]

        # ---- foydalanuvchilar
        db.add_all([
            User(email="admin@yolda.uz", password_hash=hash_password("admin123"), full_name="Admin", role="platform_admin"),
            User(email="operator@yolda.uz", password_hash=hash_password("operator123"), full_name="Nigora Saidova", role="operator"),
            User(email="mondi@yolda.uz", password_hash=hash_password("mondi123"), full_name="Lola Ahmedova",
                 role="restaurant_staff", restaurant_id=rests[0].id),
        ])

        # ---- kuryerlar
        names = set()
        couriers: list[Courier] = []
        pinfls = set()
        states = STATES[:]
        R.shuffle(states)
        vehicles = VEHICLES[:]
        R.shuffle(vehicles)
        targets = [-R.randrange(2, 47) * 10000 for _ in range(12)] + [R.randrange(2, 38) * 10000 for _ in range(14)]
        R.shuffle(targets)
        firsts = FIRST_NAMES[:24]
        R.shuffle(firsts)
        offline_idx = [i for i, s in enumerate(states) if s == "offline"]
        blocked_idx = offline_idx[0]
        for i in range(26):
            female = i >= 24
            fn = "Madina" if i == 24 else "Dilnoza" if i == 25 else firsts[i % 24]
            ln = LAST_NAMES[i] if not female else LAST_NAMES[24 + (i - 24)]
            while True:
                pf = "".join(str(R.randint(0, 9)) for _ in range(14))
                if pf not in pinfls:
                    pinfls.add(pf)
                    break
            v = vehicles[i]
            st = states[i]
            c = Courier(number=180 + i, first_name=fn, last_name=ln,
                        phone=rand_phone(R)[4:], pinfl=pf, vehicle=v, plate=fmt_plate() if v in ("Skuter", "Avto") else "—",
                        shift=R.choice(["08:00–20:00", "09:00–21:00", "10:00–22:00", "11:00–23:00"]),
                        rating=round(R.uniform(4.5, 5.0), 1), account_status="blocked" if i == blocked_idx else "active",
                        work_status=st, balance=0, is_female=female, avatar_seed=R.randint(1, 10_000),
                        settled_at=today0 - timedelta(days=R.randint(1, 5)) + timedelta(hours=9),
                        created_at=now - timedelta(days=R.randint(30, 400)))
            couriers.append(c)
            db.add(c)
        await db.flush()
        active_couriers = [c for c in couriers if c.account_status == "active"]
        ledger: list[LedgerEntry] = []

        # ---- 30 kunlik tarix
        hist: list[Order] = []
        for k in range(29, -1, -1):
            day = local_now.date() - timedelta(days=k)
            n = round(96 * COEF[day.weekday()] * R.uniform(0.93, 1.07))
            for _ in range(n):
                hour = R.choices(range(24), HOUR_W)[0]
                created = datetime.combine(day, datetime.min.time(), tzinfo=TZ) + timedelta(hours=hour, minutes=R.randint(0, 59), seconds=R.randint(0, 59))
                if created > now - timedelta(minutes=50):
                    continue
                r = R.choices(rests, REST_W)[0]
                method = R.choices(PAYS, PAY_W)[0]
                cancelled = R.random() < 0.045
                courier = R.choice(couriers)
                o = build_order(r, created, method, max_km(courier.vehicle))
                if cancelled:
                    reason = R.choice(CANCEL_REASONS)
                    o.status, o.cancelled_at, o.cancel_reason = "cancelled", created + timedelta(minutes=R.randint(2, 15)), reason
                    if reason == "Onlayn to'lov o'tmadi" and method != "Naqd":
                        o.pay_status = "failed"
                    elif method == "Naqd":
                        o.pay_status = "void"
                    else:
                        o.pay_status = "refunded"
                else:
                    mins = int(max(12, min(75, 16 + o.distance_km * 2.4 + R.gauss(0, 6) + (R.random() < 0.07) * 14)))
                    o.status, o.courier_id = "delivered", courier.id
                    o.delivery_minutes, o.is_late = mins, mins > 45
                    o.assigned_at = created + timedelta(minutes=R.randint(1, 4))
                    o.picked_at = created + timedelta(minutes=min(mins - 6, o.prep_minutes + R.randint(2, 6)))
                    o.delivered_at = created + timedelta(minutes=mins)
                    o.ready_at = created + timedelta(minutes=o.prep_minutes)
                    if method == "Naqd":
                        o.pay_status = "collected"
                    if R.random() < 0.55:
                        o.customer_rating = R.choices([5, 4, 3, 2, 1], [70, 20, 6, 2, 2])[0]
                hist.append(o)
        for i in range(0, len(hist), 400):
            db.add_all(hist[i:i + 400])
            await db.flush()
            for o in hist[i:i + 400]:
                for it in o._items:  # type: ignore[attr-defined]
                    db.add(OrderItem(order_id=o.id, **it))
        # bugungi yetkazishlar -> ledger
        for o in hist:
            if o.status == "delivered" and o.delivered_at >= today0:
                ledger.append(LedgerEntry(courier_id=o.courier_id, type="earn", amount=courier_earning(o.delivery_fee),
                                          order_id=o.id, note="Yetkazish haqi", created_at=o.delivered_at))
                if o.pay_method == "Naqd":
                    ledger.append(LedgerEntry(courier_id=o.courier_id, type="cash", amount=-o.total, order_id=o.id,
                                              note="Naqd pul mijozdan olindi", created_at=o.delivered_at))

        # ---- faol buyurtmalar va kuryer joylashuvi
        def center():
            return rand_point(41.3111, 69.2797, 0.5, 7)

        by_state: dict[str, list[Courier]] = {}
        for c, s in zip(couriers, states):
            by_state.setdefault(s, []).append(c)
        over_limit = {c.id for c, t in zip(couriers, targets) if t < -settings.CASH_LIMIT}

        def active_order(c: Courier, status: str, ago_min: int, queued=False):
            r = R.choice(open_rests)
            method = R.choices(PAYS, PAY_W)[0]
            if method == "Naqd" and c.id in over_limit:
                method = "Payme"
            created = now - timedelta(minutes=ago_min)
            o = build_order(r, created, method, max_km(c.vehicle))
            o.status, o.courier_id, o.assigned_at = status, c.id, created + timedelta(minutes=1)
            o.ready_at = created + timedelta(minutes=o.prep_minutes)
            if queued:
                o.queued, o.queue_position = True, 1
            db.add(o)
            return o, r

        pending_orders: list[tuple[Order, Courier, Restaurant, str]] = []
        for c in by_state.get("delivering", []):
            o, r = active_order(c, "onway", R.randint(14, 38))
            o.picked_at = o.created_at + timedelta(minutes=o.prep_minutes)
            t = R.uniform(0.15, 0.8)
            c.lat, c.lng = r.lat + (o.lat - r.lat) * t, r.lng + (o.lng - r.lng) * t
            pending_orders.append((o, c, r, "delivering"))
        for c in by_state.get("pickup", []):
            o, r = active_order(c, "assigned", R.randint(3, 12))
            c.lat, c.lng = rand_point(r.lat, r.lng, 0.4, 1.6)
            pending_orders.append((o, c, r, "pickup"))
        # navbatdagi buyurtma (1 ta kuryerga)
        qc = by_state["delivering"][0]
        qo, _ = active_order(qc, "assigned", 6, queued=True)
        for c in by_state.get("idle", []):
            c.lat, c.lng = center()
            c.idle_since = now - timedelta(minutes=R.randint(1, 14))
            c.online_since = now - timedelta(hours=R.randint(1, 6))
        for c in by_state.get("break", []):
            c.lat, c.lng = center()
            c.break_until = now + timedelta(minutes=R.randint(4, 12))
            c.online_since = now - timedelta(hours=R.randint(2, 6))
        for c in by_state.get("offline", []):
            c.lat, c.lng = center()
        for o, c, r, ws in pending_orders:
            c.work_status = ws
            c.online_since = now - timedelta(hours=R.randint(1, 7))
        await db.flush()
        for o, c, r, ws in pending_orders:
            c.current_order_id = o.id
        for o in [p[0] for p in pending_orders] + [qo]:
            for it in o._items:  # type: ignore[attr-defined]
                db.add(OrderItem(order_id=o.id, **it))
        for c in couriers:
            c.location_updated_at = now

        # ---- 4 ta yangi buyurtma
        new_orders = []
        for _ in range(4):
            r = R.choice(open_rests)
            created = now - timedelta(seconds=R.randint(10, 50))
            o = build_order(r, created, R.choices(PAYS, PAY_W)[0], 5)
            db.add(o)
            new_orders.append(o)
        await db.flush()
        for o in new_orders:
            for it in o._items:  # type: ignore[attr-defined]
                db.add(OrderItem(order_id=o.id, **it))

        # ---- balanslar (ledger yig'indisiga teng bo'lishi uchun ochilish yozuvi)
        sums: dict[int, int] = {}
        for e in ledger:
            sums[e.courier_id] = sums.get(e.courier_id, 0) + e.amount
        for c, tgt in zip(couriers, targets):
            diff = tgt - sums.get(c.id, 0)
            if diff:
                ledger.append(LedgerEntry(courier_id=c.id, type="fix" if diff > 0 else "cash", amount=diff, order_id=None,
                                          note="Oldingi hisob-kitob qoldig'i", created_at=today0 - timedelta(minutes=1)))
            c.balance = tgt
        db.add_all(ledger)

        # ---- shikoyatlar
        today_deliv = [o for o in hist if o.status == "delivered" and o.delivered_at >= today0] or \
                      [o for o in hist if o.status == "delivered"][-5:]
        for o, txt in zip(R.sample(today_deliv, 2), ["Buyurtma sovuq yetib keldi", "Ichimlik yetishmayapti"]):
            db.add(Complaint(order_id=o.id, restaurant_id=o.restaurant_id, text=txt, customer_name=o.customer_name,
                             status="open", created_at=now - timedelta(minutes=R.randint(5, 40))))

        # ---- feed
        samples = [("Yangi buyurtma <b>#{}</b> · {}", "brand"), ("Yetkazildi: <b>#{}</b> · {}", "grey"),
                   ("Olib ketdi: <b>#{}</b> · {}", "teal"), ("To'lov tasdiqlandi: <b>#{}</b> · {}", "teal")]
        recent = [o for o in hist if o.status == "delivered"][-12:]
        for i, o in enumerate(recent):
            tpl, col = samples[i % len(samples)]
            rest = next(r for r in rests if r.id == o.restaurant_id)
            html = (tpl.format(o.id, rest.name) if "{}" in tpl and tpl.count("{}") == 2 else tpl.format(o.id))
            db.add(FeedEvent(created_at=now - timedelta(minutes=2 * (len(recent) - i)), html_text=html, color=col,
                             restaurant_id=o.restaurant_id))
        await db.commit()

    Path(__file__).resolve().parent.parent.joinpath(".mondi_key").write_text(mondi_key)
    print("=" * 60)
    print("Seed tayyor.")
    print("  admin@yolda.uz / admin123   (platform_admin)")
    print("  operator@yolda.uz / operator123   (operator)")
    print("  mondi@yolda.uz / mondi123   (restaurant_staff, Mondi kafe)")
    print(f"Mondi kafe test API kaliti: {mondi_key}")
    print("  (backend/.mondi_key fayliga ham saqlandi)")
    print("=" * 60)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main("--reset" in sys.argv))
