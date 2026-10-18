from datetime import datetime, timedelta, timezone

from app.config import ISSUES, SLA, TRANSPORTS
from app.services.geo import haversine

PICKUP_STAGE_MIN_KM = 3.0


def issue_delay(kind: str | None) -> int:
    return ISSUES[kind]["delay"] if kind in ISSUES else 0


def compute_eta(order, courier, restaurant, open_issue_kind: str | None = None, now: datetime | None = None) -> dict | None:
    """Faol buyurtma uchun ETA. order/courier/restaurant — ORM yoki oddiy obyektlar."""
    now = now or datetime.now(timezone.utc)
    if courier is None or courier.lat is None or order.status not in ("assigned", "onway"):
        return None
    speed = TRANSPORTS.get(courier.vehicle, TRANSPORTS["Skuter"])["speed"]
    pickup = order.status == "assigned" and not order.queued
    has_cust = order.lat is not None and order.lng is not None
    if pickup:
        px, py = (order.handoff_lat, order.handoff_lng) if order.handoff_lat is not None else (restaurant.lat, restaurant.lng)
        to_point = haversine(courier.lat, courier.lng, px, py)
        pt_cust = haversine(px, py, order.lat, order.lng) if has_cust else (order.distance_km or 3.0)
        remaining = to_point + pt_cust
        stage_total = max(to_point, PICKUP_STAGE_MIN_KM)
        progress = 1 - to_point / stage_total
    else:
        remaining = haversine(courier.lat, courier.lng, order.lat, order.lng) if has_cust else \
            max(0.3, (order.distance_km or 3.0) * 0.5)
        stage_total = max(order.distance_km or remaining, remaining, 0.1)
        progress = 1 - remaining / stage_total
    progress = min(1.0, max(0.0, progress))
    delay = issue_delay(open_issue_kind)
    eta_min = max(1, round(remaining / speed * 60 + (2 if pickup else 0) + delay))
    elapsed = max(0, (now - order.created_at).total_seconds() / 60)
    total = elapsed + eta_min
    return {
        "stage": "pickup" if pickup else "delivering",
        "eta_min": eta_min,
        "remaining_km": round(remaining, 1),
        "elapsed_min": round(elapsed),
        "total_min": round(total),
        "late": total > SLA,
        "over": round(total - SLA) if total > SLA else 0,
        "progress": round(progress, 3),
        "bar_percent": round((progress * 35 if pickup else 35 + progress * 65), 1),
        "delay_min": delay,
        "arrive_at": (now + timedelta(minutes=eta_min)).isoformat(),
    }
