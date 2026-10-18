from collections import defaultdict
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.config import SLA
from app.models import Courier, Order, Restaurant
from app.services.alerts import active_context
from app.services.ledger import courier_earning
from app.services.serializers import iso, now_utc

TZ = ZoneInfo("Asia/Tashkent")
WEEKDAYS = ["Yak", "Du", "Se", "Chor", "Pay", "Ju", "Sha"]


def local(d: datetime) -> datetime:
    return d.astimezone(TZ)


def weekday_name(d: date) -> str:
    return WEEKDAYS[(d.weekday() + 1) % 7]


def day_start(d: date) -> datetime:
    return datetime.combine(d, time(0), tzinfo=TZ)


def resolve_period(period: str = "today", from_: date | None = None, to_: date | None = None, now: datetime | None = None) -> dict:
    now = (now or now_utc()).astimezone(TZ)
    t0 = day_start(now.date())
    day = timedelta(days=1)
    label = "oldingi davrga nisbatan"
    if period == "yesterday":
        start, end = t0 - day, t0
        pstart, pend = start - day, start
        label = "oldingi kunga nisbatan"
    elif period == "week":
        start, end = t0 - 6 * day, t0 + day
        pstart, pend = start - 7 * day, start
    elif period == "month":
        start, end = t0 - 29 * day, t0 + day
        pstart, pend = start - 30 * day, start
    elif period == "range" and from_ and to_:
        if to_ < from_:
            from_, to_ = to_, from_
        if (to_ - from_).days > 365:
            from_ = to_ - timedelta(days=365)
        start, end = day_start(from_), day_start(to_) + day
        n = end - start
        pstart, pend = start - n, start
    else:
        period = "today"
        start, end = t0, t0 + day
        pstart = t0 - day
        pend = pstart + (now - t0)
        label = "kechagiga nisbatan"
    days = round((end - start).total_seconds() / 86400)
    last = end - day
    return {"key": period, "start": start, "end": end, "prev_start": pstart, "prev_end": pend,
            "prev_full_end": pstart + (end - start), "days": days, "hourly": days == 1, "compare_label": label,
            "from": start.date().isoformat(), "to": last.date().isoformat(), "now": now}


COLS = (Order.id, Order.created_at, Order.status, Order.total, Order.delivery_fee, Order.delivery_minutes,
        Order.is_late, Order.courier_id, Order.restaurant_id, Order.pay_method, Order.cancel_reason,
        Order.customer_rating, Order.pay_status)


async def fetch(db, start, end, rid=None):
    q = select(*COLS).where(Order.created_at >= start, Order.created_at < end)
    if rid:
        q = q.where(Order.restaurant_id == rid)
    return (await db.execute(q)).all()


def pct(cur, prev):
    if not prev:
        return None
    return round((cur - prev) / prev * 100)


def basic(rows) -> dict:
    deliv = [r for r in rows if r.status == "delivered"]
    canc = [r for r in rows if r.status == "cancelled"]
    dm = [r.delivery_minutes for r in deliv if r.delivery_minutes is not None]
    return {"orders": len(rows), "delivered": len(deliv), "cancelled": len(canc),
            "revenue": sum(r.total for r in deliv), "avg_delivery": round(sum(dm) / len(dm)) if dm else 0,
            "late": sum(1 for r in deliv if r.is_late),
            "cancel_rate": round(len(canc) / len(rows) * 100, 1) if rows else 0.0}


def series(rows, per: dict, key_fn, size_fn_values):
    pass


def chart(rows, p: dict, prev_rows=None, only_past=True) -> dict:
    """Soatlar yoki kunlar bo'yicha buyurtmalar soni (tanlangan va oldingi davr)."""
    now = p["now"]
    if p["hourly"]:
        cur, prev = [0] * 24, [0] * 24
        for r in rows:
            cur[local(r.created_at).hour] += 1
        for r in prev_rows or []:
            prev[local(r.created_at).hour] += 1
        if p["key"] == "today":
            cur = [v if h <= now.hour else None for h, v in enumerate(cur)]
        return {"mode": "hours", "labels": [f"{h:02d}" for h in range(24)], "current": cur, "previous": prev}
    n = p["days"]
    cur, prev = [0] * n, [0] * n
    for r in rows:
        i = (local(r.created_at).date() - p["start"].date()).days
        if 0 <= i < n:
            cur[i] += 1
    for r in prev_rows or []:
        i = (local(r.created_at).date() - p["prev_start"].date()).days
        if 0 <= i < n:
            prev[i] += 1
    labels = [(p["start"].date() + timedelta(days=i)).strftime("%d.%m") for i in range(n)]
    return {"mode": "days", "labels": labels, "current": cur, "previous": prev}


def delivered_other_chart(rows, p: dict) -> dict:
    if p["hourly"]:
        n, labels = 24, [f"{h:02d}" for h in range(24)]
        idx = lambda r: local(r.created_at).hour  # noqa
    else:
        n = p["days"]
        labels = [(p["start"].date() + timedelta(days=i)).strftime("%d.%m") for i in range(n)]
        idx = lambda r: (local(r.created_at).date() - p["start"].date()).days  # noqa
    d, o = [0] * n, [0] * n
    for r in rows:
        i = idx(r)
        if 0 <= i < n:
            (d if r.status == "delivered" else o)[i] += 1
    return {"mode": "hours" if p["hourly"] else "days", "labels": labels, "delivered": d, "other": o}


async def overview(db, period: str, from_, to_, rid: int | None, forced_rid: int | None) -> dict:
    p = resolve_period(period, from_, to_)
    rows = await fetch(db, p["start"], p["end"], rid)
    prev_all = await fetch(db, p["prev_start"], p["prev_full_end"], rid)
    prev_rows = [r for r in prev_all if r.created_at < p["prev_end"]]
    cur, prv = basic(rows), basic(prev_rows)

    def kpi(k, lower_better=False):
        d = pct(cur[k], prv[k])
        return {"value": cur[k], "prev": prv[k], "delta_pct": d,
                "good": None if d is None or d == 0 else ((d < 0) if lower_better else (d > 0))}

    ctx = await active_context(db, rid)
    searching = sum(1 for x in ctx if x["order"].status == "new")
    pickup = sum(1 for x in ctx if x["order"].status == "assigned")
    delivering = sum(1 for x in ctx if x["order"].status == "onway")
    issues = sum(1 for x in ctx if x["issue"])
    risk = sum(1 for x in ctx if not x["issue"] and x["eta"] and x["eta"]["late"])

    couriers = (await db.execute(select(Courier))).scalars().all()
    online = [c for c in couriers if c.account_status == "active" and c.work_status != "offline"]
    onroute = [c for c in online if c.work_status in ("delivering", "pickup")]

    # restoranlar (faqat majburiy filtr)
    rows_all = rows if rid == forced_rid else await fetch(db, p["start"], p["end"], forced_rid)
    rests = {r.id: r for r in (await db.execute(select(Restaurant))).scalars()}
    cnt = defaultdict(int)
    for r in rows_all:
        cnt[r.restaurant_id] += 1
    rest_list = [{"id": i, "name": rests[i].name, "color": rests[i].color, "count": n}
                 for i, n in sorted(cnt.items(), key=lambda kv: -kv[1])[:7]]

    top = await top_couriers(db, rows, 7)
    avg = kpi("avg_delivery", True)
    return {
        "period": {"key": p["key"], "from": p["from"], "to": p["to"], "days": p["days"],
                   "compare_label": p["compare_label"]},
        "kpis": {
            "orders": kpi("orders"),
            "active": {"value": len(ctx), "searching": searching},
            "delivered": kpi("delivered"),
            "cancelled": {**kpi("cancelled", True), "rate": cur["cancel_rate"], "norm": 5},
            "avg_delivery": {**avg, "late_count": cur["late"], "sla": SLA},
            "revenue": kpi("revenue"),
        },
        "chart": chart(rows, p, prev_all),
        "flow": {"searching": searching, "pickup": pickup, "delivering": delivering, "issues": issues,
                 "risk": risk, "total": len(ctx)},
        "couriers": {"total": len(couriers), "online": len(online), "on_route": len(onroute),
                     "offline": len(couriers) - len(online)},
        "restaurants": rest_list,
        "top_couriers": top,
    }


async def top_couriers(db, rows, limit: int) -> list[dict]:
    agg = defaultdict(lambda: {"n": 0, "amount": 0, "earned": 0, "mins": [], "late": 0, "ratings": []})
    for r in rows:
        if r.status != "delivered" or not r.courier_id:
            continue
        a = agg[r.courier_id]
        a["n"] += 1
        a["amount"] += r.total
        a["earned"] += courier_earning(r.delivery_fee)
        a["late"] += 1 if r.is_late else 0
        if r.delivery_minutes is not None:
            a["mins"].append(r.delivery_minutes)
        if r.customer_rating:
            a["ratings"].append(r.customer_rating)
    ids = sorted(agg, key=lambda i: -agg[i]["n"])[:limit]
    if not ids:
        return []
    cs = {c.id: c for c in (await db.execute(select(Courier).where(Courier.id.in_(ids)))).scalars()}
    out = []
    for i in ids:
        a, c = agg[i], cs[i]
        out.append({"id": i, "number": c.number, "name": f"{c.first_name} {c.last_name}", "avatar_seed": c.avatar_seed,
                    "is_female": c.is_female, "delivered": a["n"], "amount": a["amount"], "earned": a["earned"],
                    "avg_minutes": round(sum(a["mins"]) / len(a["mins"])) if a["mins"] else 0, "late": a["late"],
                    "rating": round(sum(a["ratings"]) / len(a["ratings"]), 2) if a["ratings"] else float(c.rating)})
    return out


def summary_for(rows) -> dict:
    b = basic(rows)
    fin = b["delivered"] + b["cancelled"]
    return {"orders": b["orders"], "revenue": b["revenue"],
            "avg_check": round(b["revenue"] / b["delivered"]) if b["delivered"] else 0,
            "success_pct": round(b["delivered"] / fin * 100, 1) if fin else 0.0,
            "avg_delivery": b["avg_delivery"], "delivered": b["delivered"], "cancelled": b["cancelled"]}


async def analytics(db, days: int, rid: int | None, forced_rid: int | None) -> dict:
    days = days if days in (7, 14, 30) else 7
    now = now_utc().astimezone(TZ)
    t0 = day_start(now.date())
    start, end = t0 - timedelta(days=days - 1), t0 + timedelta(days=1)
    rows = await fetch(db, start, end, rid)
    labels, delivered, cancelled, revenue = [], [0] * days, [0] * days, [0.0] * days
    for i in range(days):
        d = start.date() + timedelta(days=i)
        labels.append(weekday_name(d) if days == 7 else d.strftime("%d.%m"))
    hours = defaultdict(list)
    for r in rows:
        i = (local(r.created_at).date() - start.date()).days
        if r.status == "delivered":
            delivered[i] += 1
            revenue[i] += r.total
            if r.delivery_minutes is not None:
                hours[local(r.created_at).hour].append(r.delivery_minutes)
        elif r.status == "cancelled":
            cancelled[i] += 1
    # restoranlar tushumi
    rows_all = rows if rid == forced_rid else await fetch(db, start, end, forced_rid)
    rests = {r.id: r for r in (await db.execute(select(Restaurant))).scalars()}
    rv = defaultdict(lambda: [0, 0])
    for r in rows_all:
        if r.status == "delivered":
            rv[r.restaurant_id][0] += 1
            rv[r.restaurant_id][1] += r.total
    rest_rev = [{"id": i, "name": rests[i].name, "color": rests[i].color, "count": v[0], "revenue": v[1]}
                for i, v in sorted(rv.items(), key=lambda kv: -kv[1][1])]
    pay = defaultdict(int)
    for r in rows:
        pay[r.pay_method] += 1
    total = sum(pay.values()) or 1
    payments = [{"method": m, "count": pay.get(m, 0), "percent": round(pay.get(m, 0) / total * 100, 1)}
                for m in ("Payme", "Naqd", "Click", "Karta")]
    reasons = defaultdict(int)
    for r in rows:
        if r.status == "cancelled":
            reasons[r.cancel_reason or "Boshqa"] += 1
    return {
        "range": {"from": start.date().isoformat(), "to": (end - timedelta(days=1)).date().isoformat(), "days": days},
        "daily": {"labels": labels, "delivered": delivered, "cancelled": cancelled},
        "revenue_mln": {"labels": labels, "values": [round(v / 1e6, 1) for v in revenue]},
        "hourly_avg_delivery": {"labels": [f"{h:02d}" for h in range(24)],
                                "values": [round(sum(hours[h]) / len(hours[h])) if hours[h] else 0 for h in range(24)]},
        "restaurants": rest_rev,
        "couriers": await top_couriers(db, rows, 8),
        "payments": payments,
        "cancel_reasons": [{"reason": k, "count": v} for k, v in sorted(reasons.items(), key=lambda kv: -kv[1])],
    }
