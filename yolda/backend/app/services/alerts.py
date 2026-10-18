from datetime import timedelta

from sqlalchemy import select

from app.config import ISSUES, ORDER_STATUS, SLA, settings
from app.models import Complaint, Courier, DismissedAlert, Order, OrderIssue, Restaurant
from app.services.eta import compute_eta
from app.services.serializers import ISSUE_BUTTONS, BUTTON_LABELS, full_name, iso, now_utc


async def active_context(db, rid: int | None = None, now=None) -> list[dict]:
    """Faol buyurtmalar: kuryer, restoran, ochiq muammo va ETA bilan."""
    now = now or now_utc()
    q = select(Order).where(Order.status.in_(("new", "assigned", "onway")))
    if rid:
        q = q.where(Order.restaurant_id == rid)
    orders = (await db.execute(q.order_by(Order.created_at))).scalars().all()
    if not orders:
        return []
    cids = {o.courier_id for o in orders if o.courier_id}
    couriers = {c.id: c for c in (await db.execute(select(Courier).where(Courier.id.in_(cids)))).scalars()} if cids else {}
    rests = {r.id: r for r in (await db.execute(select(Restaurant))).scalars()}
    oids = [o.id for o in orders]
    issues = {i.order_id: i for i in (await db.execute(select(OrderIssue).where(
        OrderIssue.order_id.in_(oids), OrderIssue.ended_at.is_(None)))).scalars()}
    out = []
    for o in orders:
        c = couriers.get(o.courier_id)
        r = rests[o.restaurant_id]
        iss = issues.get(o.id)
        eta = compute_eta(o, c, r, iss.kind if iss else None, now) if c else None
        out.append({"order": o, "courier": c, "rest": r, "issue": iss, "eta": eta})
    return out


def _ago_min(d, now) -> int:
    return int((now - d).total_seconds() // 60)


async def build_alerts(db, user, rid: int | None) -> list[dict]:
    now = now_utc()
    items: list[dict] = []
    ctx = await active_context(db, rid, now)

    for x in ctx:
        o, c, r, iss, eta = x["order"], x["courier"], x["rest"], x["issue"], x["eta"]
        if iss:
            meta = ISSUES[iss.kind]
            text = (f"{full_name(c)} · {r.name} → {o.district} · {_ago_min(iss.started_at, now)} daq oldin · "
                    f"kechikish +{meta['delay']} daq")
            if iss.kind == "vehicle":
                text += " · tizim 1 daqiqada avtomatik qayta taqsimlaydi"
            items.append({"key": f"issue:{iss.id}", "kind": "issue", "severity": "red" if iss.kind == "vehicle" else "amber",
                          "title": f"#{o.id}: {meta['text']}", "text": text, "dismissible": False,
                          "order_id": o.id, "courier_id": c.id if c else None, "restaurant_id": r.id,
                          "created_at": iso(iss.started_at), "issue_kind": iss.kind,
                          "customer_phone": o.customer_phone, "restaurant_phone": r.phone,
                          "actions": [{"key": b, "label": BUTTON_LABELS[b]} for b in ISSUE_BUTTONS[iss.kind]]})
        elif eta and eta["late"]:
            items.append({"key": f"late:{o.id}", "kind": "late", "severity": "red" if eta["over"] > 10 else "amber",
                          "title": f"#{o.id} kechikmoqda — jami ~{eta['total_min']} daq (me'yor {SLA})",
                          "text": f"{full_name(c)} · {r.name} → {o.district}, yana {eta['eta_min']} daq",
                          "dismissible": True, "order_id": o.id, "courier_id": c.id, "restaurant_id": r.id,
                          "created_at": iso(o.created_at), "customer_phone": o.customer_phone,
                          "actions": [{"key": "view_courier", "label": "Kuryerni ko'rish"},
                                      {"key": "notify_customer", "label": "Mijozga xabar"}]})
        if o.status == "new" and o.pay_status != "pending":
            wait = _ago_min(o.search_started_at or o.created_at, now)
            if (now - o.created_at).total_seconds() >= 120:
                m = _ago_min(o.created_at, now)
                items.append({"key": f"nocourier:{o.id}", "kind": "nocourier", "severity": "red" if m >= 5 else "amber",
                              "title": f"#{o.id} uchun {m} daqiqadan beri mos kuryer topilmadi",
                              "text": f"{r.name} → {o.district} · {o.pay_method} · {len(o.declined_courier_ids or [])} ta kuryer "
                                      f"rad etdi · tizim qidirishda davom etmoqda",
                              "dismissible": True, "order_id": o.id, "courier_id": None, "restaurant_id": r.id,
                              "created_at": iso(o.created_at),
                              "actions": [{"key": "details", "label": "Batafsil"}, {"key": "cancel", "label": "Bekor qilish"}]})

    # to'lov o'tmadi (15 daq)
    q = select(Order).where(Order.pay_status == "failed", Order.cancelled_at >= now - timedelta(minutes=15))
    if rid:
        q = q.where(Order.restaurant_id == rid)
    for o in (await db.execute(q)).scalars():
        items.append({"key": f"payfail:{o.id}", "kind": "payfail", "severity": "grey",
                      "title": f"#{o.id}: onlayn to'lov o'tmadi",
                      "text": f"{o.customer_name} · {o.pay_method} · {o.total:,} so'm".replace(",", " "),
                      "dismissible": True, "order_id": o.id, "courier_id": None, "restaurant_id": o.restaurant_id,
                      "created_at": iso(o.cancelled_at), "customer_phone": o.customer_phone,
                      "actions": [{"key": "write_customer", "label": "Mijozga yozish"}]})

    # naqd limit (faqat platforma xodimlari)
    if user.role != "restaurant_staff":
        over = (await db.execute(select(Courier).where(Courier.balance < -settings.CASH_LIMIT,
                                                       Courier.account_status == "active")
                                 .order_by(Courier.balance))).scalars().all()
        if over:
            names = ", ".join(f"{full_name(c)} ({c.balance:,})".replace(",", " ") for c in over[:3])
            items.append({"key": "cash", "kind": "cash", "severity": "amber",
                          "title": f"{len(over)} ta kuryer naqd pul limitidan oshgan ({settings.CASH_LIMIT:,} so'm)".replace(",", " "),
                          "text": f"{names} — tizim ularga naqd buyurtma bermaydi", "dismissible": True,
                          "order_id": None, "courier_id": None, "restaurant_id": None, "created_at": iso(now),
                          "actions": [{"key": "topup", "label": "Balansni to'ldirish"}]})

    # pauzadagi restoranlar
    rq = select(Restaurant).where(Restaurant.status == "paused")
    if rid:
        rq = rq.where(Restaurant.id == rid)
    for r in (await db.execute(rq)).scalars():
        items.append({"key": f"rest:{r.id}", "kind": "restpaused", "severity": "grey",
                      "title": f"{r.name} buyurtma qabul qilmayapti", "text": r.pause_reason or "Sabab ko'rsatilmagan",
                      "dismissible": True, "order_id": None, "courier_id": None, "restaurant_id": r.id,
                      "created_at": iso(r.created_at), "actions": [{"key": "resume_restaurant", "label": "Faollashtirish"}]})

    # shikoyatlar
    cq = select(Complaint, Restaurant).join(Restaurant, Restaurant.id == Complaint.restaurant_id).where(
        Complaint.status == "open")
    if rid:
        cq = cq.where(Complaint.restaurant_id == rid)
    for cm, r in (await db.execute(cq)).all():
        items.append({"key": f"complaint:{cm.id}", "kind": "complaint", "severity": "violet",
                      "title": f"Mijoz shikoyati · #{cm.order_id}", "text": f"{cm.customer_name}: {cm.text}",
                      "dismissible": True, "order_id": cm.order_id, "courier_id": None, "restaurant_id": r.id,
                      "created_at": iso(cm.created_at), "restaurant_phone": r.phone,
                      "actions": [{"key": "write_restaurant", "label": "Restoranga yozish"}]})

    dismissed = set((await db.execute(select(DismissedAlert.alert_key).where(DismissedAlert.user_id == user.id))).scalars())
    return [a for a in items if a["key"] not in dismissed]
