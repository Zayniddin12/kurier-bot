"""Xarita va jonli yangilanishlar uchun kuryer yozuvi."""
from sqlalchemy import select

from app.config import ISSUES
from app.models import Courier, Order, OrderIssue, Restaurant
from app.services.eta import compute_eta
from app.services.events import emit
from app.services.serializers import WORK_LABELS, iso, line_state, now_utc


def map_entry(c: Courier, order: Order | None, rest: Restaurant | None, issue: OrderIssue | None, now=None) -> dict:
    now = now or now_utc()
    eta = compute_eta(order, c, rest, issue.kind if issue else None, now) if order and rest else None
    wl = WORK_LABELS[c.work_status]
    route = None
    if order:
        pickup = order.status == "assigned"
        if order.handoff_lat is not None and pickup:
            rp = {"lat": order.handoff_lat, "lng": order.handoff_lng}
        else:
            rp = {"lat": rest.lat, "lng": rest.lng} if rest else None
        route = {"stage": "pickup" if pickup else "delivering", "restaurant": rp if pickup else None,
                 "customer": {"lat": order.lat, "lng": order.lng} if order.lat is not None else None}
    return {
        "id": c.id, "number": c.number, "name": f"{c.first_name} {c.last_name}", "phone": c.phone,
        "vehicle": c.vehicle, "avatar_seed": c.avatar_seed, "is_female": c.is_female, "rating": float(c.rating),
        "lat": c.lat, "lng": c.lng, "work_status": c.work_status, "work_label": wl[0], "work_color": wl[1],
        "account_status": c.account_status, "line_state": line_state(c),
        "location_updated_at": iso(c.location_updated_at), "current_order_id": c.current_order_id,
        "order": ({"id": order.id, "status": order.status, "customer_name": order.customer_name,
                   "customer_phone": order.customer_phone, "address": order.address, "district": order.district,
                   "restaurant_id": order.restaurant_id, "restaurant_name": rest.name if rest else None,
                   "pay_method": order.pay_method} if order else None),
        "route": route, "eta": eta,
        "issue": {"kind": issue.kind, "text": ISSUES[issue.kind]["text"]} if issue else None,
        "late": bool(eta and eta["late"]),
    }


async def courier_changed(db, c: Courier):
    order = await db.get(Order, c.current_order_id) if c.current_order_id else None
    rest = await db.get(Restaurant, order.restaurant_id) if order else None
    issue = None
    if order:
        issue = (await db.execute(select(OrderIssue).where(
            OrderIssue.order_id == order.id, OrderIssue.ended_at.is_(None)))).scalars().first()
    emit(db, "courier.updated", map_entry(c, order, rest, issue), rest.id if rest else None)
