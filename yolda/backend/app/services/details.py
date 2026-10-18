from datetime import timedelta

from sqlalchemy import select

from app.models import Courier, Order, OrderIssue, OrderItem, OrderOffer, Restaurant
from app.services.eta import compute_eta
from app.services.serializers import (courier_brief, full_name, iso, issue_dict, money_split, now_utc, order_row,
                                      timeline)


async def order_detail(db, o: Order) -> dict:
    now = now_utc()
    r = await db.get(Restaurant, o.restaurant_id)
    c = await db.get(Courier, o.courier_id) if o.courier_id else None
    items = (await db.execute(select(OrderItem).where(OrderItem.order_id == o.id).order_by(OrderItem.id))).scalars().all()
    issues = (await db.execute(select(OrderIssue).where(OrderIssue.order_id == o.id).order_by(OrderIssue.started_at))).scalars().all()
    open_i = next((i for i in issues if i.ended_at is None), None)
    d = order_row(o, r, c)
    d.update({
        "note": o.note,
        "restaurant": {"id": r.id, "name": r.name, "color": r.color, "district": r.district, "cuisine": r.cuisine,
                       "address": r.address, "lat": r.lat, "lng": r.lng, "phone": r.phone},
        "courier": ({**courier_brief(c), "lat": c.lat, "lng": c.lng, "work_status": c.work_status} if c else None),
        "items": [{"name": i.name, "qty": i.qty, "price": i.price} for i in items],
        "eta": compute_eta(o, c, r, open_i.kind if open_i else None, now) if c and not o.queued else None,
        "issue": issue_dict(open_i, o, c, r, now) if open_i else None,
        "issues": [issue_dict(i, o, c, r, now) for i in issues],
        "payment": money_split(o),
        "timeline": timeline(o),
        "times": {"created_at": iso(o.created_at), "assigned_at": iso(o.assigned_at), "picked_at": iso(o.picked_at),
                  "delivered_at": iso(o.delivered_at), "cancelled_at": iso(o.cancelled_at)},
        "cancel_reason": o.cancel_reason, "prep_minutes": o.prep_minutes, "reassigned_count": o.reassigned_count,
        "handoff": ({"lat": o.handoff_lat, "lng": o.handoff_lng, "name": o.handoff_name}
                    if o.handoff_lat is not None else None),
        "ago_min": int((now - o.created_at).total_seconds() // 60),
        "search": None,
    })
    if o.status == "new":
        offer = (await db.execute(select(OrderOffer).where(OrderOffer.order_id == o.id, OrderOffer.result == "pending",
                                                           OrderOffer.expires_at > now))).scalars().first()
        oc = await db.get(Courier, offer.courier_id) if offer else None
        d["search"] = {"pending_payment": o.pay_status == "pending",
                       "offer_courier": {"id": oc.id, "name": full_name(oc)} if oc else None,
                       "declined_count": len(o.declined_courier_ids or []),
                       "wait_minutes": int(((now - (o.search_started_at or o.created_at)).total_seconds()) // 60)}
    return d
