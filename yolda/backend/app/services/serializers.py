from datetime import datetime, timezone

from app.config import ISSUES, ORDER_STATUS, PAY_STATUS, TRANSPORTS, settings
from app.services.ledger import courier_earning, platform_commission

ISSUE_BUTTONS = {
    "noanswer": ["call_customer", "resolve", "cancel"],
    "address": ["call_customer", "resolve"],
    "restdelay": ["call_restaurant", "resolve"],
    "vehicle": ["reassign"],
    "wrong": ["call_restaurant", "resolve", "cancel"],
}
BUTTON_LABELS = {
    "call_customer": "Mijozga qo'ng'iroq", "call_restaurant": "Restoranga qo'ng'iroq",
    "resolve": "Hal qilindi", "cancel": "Bekor qilish", "reassign": "Boshqa kuryerga o'tkazish",
}
WORK_LABELS = {
    "delivering": ("Yetkazmoqda", "teal"), "pickup": ("Restoranga yo'lda", "blue"), "idle": ("Bo'sh", "amber"),
    "break": ("Tanaffusda", "grey"), "offline": ("Smenada emas", "faint"),
}


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def iso(d):
    return d.isoformat() if d else None


def full_name(c) -> str:
    return f"{c.first_name} {c.last_name}"


def rest_brief(r) -> dict:
    return {"id": r.id, "name": r.name, "color": r.color, "district": r.district}


def courier_brief(c) -> dict | None:
    if c is None:
        return None
    return {"id": c.id, "number": c.number, "name": full_name(c), "phone": c.phone, "vehicle": c.vehicle,
            "plate": c.plate, "avatar_seed": c.avatar_seed, "is_female": c.is_female, "rating": float(c.rating)}


def line_state(c) -> str:
    if c.account_status == "blocked" or c.work_status == "offline":
        return "offline"
    if c.work_status == "break":
        return "pause"
    return "line"


def overall_status(c) -> str:
    return "blocked" if c.account_status == "blocked" else c.work_status


def order_row(o, r, c) -> dict:
    st = ORDER_STATUS[o.status]
    ps = PAY_STATUS.get(o.pay_status, (o.pay_status, "grey"))
    return {
        "id": o.id, "external_id": o.external_id, "restaurant": rest_brief(r), "created_at": iso(o.created_at),
        "status": o.status, "status_text": st[0], "status_color": st[1],
        "subtotal": o.subtotal, "delivery_fee": o.delivery_fee, "total": o.total, "distance_km": o.distance_km,
        "pay_method": o.pay_method, "pay_status": o.pay_status, "pay_status_text": ps[0], "pay_status_color": ps[1],
        "customer_name": o.customer_name, "customer_phone": o.customer_phone, "district": o.district,
        "address": o.address, "lat": o.lat, "lng": o.lng,
        "courier": courier_brief(c), "delivery_minutes": o.delivery_minutes, "is_late": o.is_late,
        "queued": o.queued, "customer_rating": o.customer_rating,
    }


def issue_dict(i, order, courier, restaurant, now=None) -> dict:
    now = now or now_utc()
    meta = ISSUES[i.kind]
    return {
        "id": i.id, "order_id": i.order_id, "courier_id": i.courier_id, "kind": i.kind, "text": meta["text"],
        "delay_min": meta["delay"], "started_at": iso(i.started_at), "ended_at": iso(i.ended_at),
        "seconds": int(((i.ended_at or now) - i.started_at).total_seconds()),
        "resolved_by": i.resolved_by, "auto_at": iso(i.auto_at),
        "buttons": [{"key": b, "label": BUTTON_LABELS[b]} for b in ISSUE_BUTTONS[i.kind]],
        "courier_name": full_name(courier) if courier else None,
        "restaurant_name": restaurant.name if restaurant else None,
        "customer_phone": order.customer_phone if order else None,
        "restaurant_phone": restaurant.phone if restaurant else None,
    }


def money_split(o) -> dict:
    fee = courier_earning(o.delivery_fee)
    d = {"method": o.pay_method, "status": o.pay_status, "status_text": PAY_STATUS[o.pay_status][0],
         "status_color": PAY_STATUS[o.pay_status][1], "subtotal": o.subtotal, "delivery_fee": o.delivery_fee,
         "total": o.total, "courier_fee": fee, "commission": platform_commission(o.delivery_fee),
         "courier_collects": o.pay_method == "Naqd", "company_due": (o.total - fee) if o.pay_method == "Naqd" else 0}
    return d


def timeline(o) -> list[dict]:
    if o.status == "cancelled":
        return [{"key": "created", "label": "Buyurtma qabul qilindi", "at": iso(o.created_at), "state": "done"},
                {"key": "cancelled", "label": f"Bekor qilindi: {o.cancel_reason or '—'}", "at": iso(o.cancelled_at),
                 "state": "cancelled"}]
    steps = [("created", "Buyurtma qabul qilindi", o.created_at),
             ("assigned", "Kuryer biriktirildi", o.assigned_at if not o.queued else None),
             ("picked", "Restorandan olib ketildi", o.picked_at),
             ("delivered", "Mijozga yetkazildi", o.delivered_at)]
    out, current_set = [], False
    for k, label, at in steps:
        if at:
            out.append({"key": k, "label": label, "at": iso(at), "state": "done"})
        elif not current_set:
            out.append({"key": k, "label": label, "at": None, "state": "current"})
            current_set = True
        else:
            out.append({"key": k, "label": label, "at": None, "state": "todo"})
    return out


def courier_row(c, today_orders=0, today_amount=0, issue=None, order=None) -> dict:
    wl = WORK_LABELS[c.work_status]
    tr = TRANSPORTS.get(c.vehicle)
    if issue:
        cur = ISSUES[issue.kind]["text"]
    elif order:
        cur = f"#{order.id}"
    else:
        cur = wl[0]
    return {
        "id": c.id, "number": c.number, "first_name": c.first_name, "last_name": c.last_name, "full_name": full_name(c),
        "phone": c.phone, "pinfl": c.pinfl, "vehicle": c.vehicle, "vehicle_name": tr["name"] if tr else c.vehicle,
        "plate": c.plate, "shift": c.shift, "rating": float(c.rating), "account_status": c.account_status,
        "work_status": c.work_status, "work_label": wl[0], "work_color": wl[1], "line_state": line_state(c),
        "overall_status": overall_status(c), "balance": c.balance, "over_limit": c.balance < -settings.CASH_LIMIT,
        "today_orders": today_orders, "today_amount": today_amount,
        "issue": {"kind": issue.kind, "text": ISSUES[issue.kind]["text"]} if issue else None,
        "current_text": cur, "current_order_id": c.current_order_id, "created_at": iso(c.created_at),
        "avatar_seed": c.avatar_seed, "is_female": c.is_female,
        "lat": c.lat, "lng": c.lng, "idle_since": iso(c.idle_since), "online_since": iso(c.online_since),
        "max_km": tr["max_km"] if tr else None, "telegram_linked": c.telegram_id is not None,
    }


def restaurant_row(r, today=0, active=0) -> dict:
    return {
        "id": r.id, "name": r.name, "cuisine": r.cuisine, "district": r.district, "address": r.address,
        "lat": r.lat, "lng": r.lng, "color": r.color, "integration_type": r.integration_type,
        "pos_system": r.pos_system, "status": r.status, "pause_reason": r.pause_reason, "rating": float(r.rating),
        "prep_minutes": r.prep_minutes, "phone": r.phone, "hours": r.hours, "manager": r.manager,
        "connected_at": iso(r.connected_at), "last_sync_at": iso(r.last_sync_at),
        "api_key_prefix": r.api_key_prefix, "webhook_url": r.webhook_url,
        "today": today, "active": active,
        "sync_ok": bool(r.last_sync_at and (now_utc() - r.last_sync_at).total_seconds() < 600),
    }
