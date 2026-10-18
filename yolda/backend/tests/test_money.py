from types import SimpleNamespace
from datetime import datetime, timedelta, timezone

from app.services.eta import compute_eta
from app.services.ledger import courier_earning, delivery_fee_for, platform_commission, salary_math


def test_delivery_fee():
    assert delivery_fee_for(0) == 7000
    assert delivery_fee_for(3.2) == 12000      # 7000 + 4800 = 11800 -> 12000
    assert delivery_fee_for(5.0) == 15000      # 14500 -> 15000 (yarimdan yuqoriga)
    assert delivery_fee_for(1.0) == 9000       # 8500 -> 9000


def test_courier_earning_and_commission():
    assert courier_earning(12000) == 10200
    assert platform_commission(12000) == 1800
    assert courier_earning(9000) + platform_commission(9000) == 9000
    assert courier_earning(15000) == 12800     # 12750 -> 12800


def test_salary_formula():
    assert salary_math(100_000, 23, 3) == {"bonus": 40_000, "fine": 15_000, "payable": 125_000}
    assert salary_math(-120_000, 9, 0)["payable"] == 0
    assert salary_math(-100_000, 10, 1)["payable"] == 0       # -100000 + 20000 - 5000 < 0
    assert salary_math(10_000, 5, 5) == {"bonus": 0, "fine": 25_000, "payable": 0}


def _o(**kw):
    base = dict(status="assigned", queued=False, created_at=datetime.now(timezone.utc) - timedelta(minutes=10),
                handoff_lat=None, handoff_lng=None, lat=41.40, lng=69.30, distance_km=5.0)
    base.update(kw)
    return SimpleNamespace(**base)


def test_eta_pickup_and_late():
    rest = SimpleNamespace(lat=41.35, lng=69.30)
    c = SimpleNamespace(lat=41.35, lng=69.30, vehicle="Skuter")
    e = compute_eta(_o(), c, rest)
    # restoran ustida: faqat restoran -> mijoz (~5.5 km / 28 km/h * 60 + 2)
    assert e["stage"] == "pickup" and e["eta_min"] == round(5.56 / 28 * 60 + 2)
    assert not e["late"]
    late = compute_eta(_o(created_at=datetime.now(timezone.utc) - timedelta(minutes=44)), c, rest)
    assert late["late"] and late["over"] == late["total_min"] - 45


def test_eta_delivering_issue_delay_and_bar():
    rest = SimpleNamespace(lat=41.35, lng=69.30)
    c = SimpleNamespace(lat=41.40, lng=69.30, vehicle="Avto")    # mijoz joyida
    e = compute_eta(_o(status="onway"), c, rest, open_issue_kind="noanswer")
    assert e["stage"] == "delivering" and e["eta_min"] == max(1, round(0 + 6))
    assert e["bar_percent"] >= 99
