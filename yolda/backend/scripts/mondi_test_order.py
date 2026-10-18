#!/usr/bin/env python3
"""Mondi kafe nomidan test buyurtma yuboradi.

Ishlatish:  python scripts/mondi_test_order.py [--url http://localhost:8000] [--key yl_live_...] [--pay Payme|Click|Karta|Naqd]
Kalit: --key, YOLDA_API_KEY muhit o'zgaruvchisi yoki backend/.mondi_key (seed yozadi).
"""
import argparse
import json
import os
import random
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("--url", default=os.getenv("YOLDA_URL", "http://localhost:8000"))
p.add_argument("--key", default=os.getenv("YOLDA_API_KEY"))
p.add_argument("--pay", default="Payme", choices=["Payme", "Click", "Karta", "Naqd"])
p.add_argument("--external-id", default=None, help="Bir xil qiymat qayta yuborilsa buyurtma takrorlanmaydi")
a = p.parse_args()

key = a.key
if not key:
    f = Path(__file__).resolve().parent.parent / ".mondi_key"
    key = f.read_text().strip() if f.exists() else None
if not key:
    sys.exit("API kalit topilmadi: --key yoki YOLDA_API_KEY bering (python -m app.seed uni chiqaradi)")

ext = a.external_id or f"MND-{int(time.time()) % 100000}"
body = {
    "external_id": ext,
    "customer": {"name": "Dilnoza A.", "phone": "+998901234567"},
    "address": {"text": "Yunusobod 4-kvartal, 12-uy, 34-xonadon", "district": "Yunusobod",
                "lat": round(41.3650 + random.uniform(-0.03, 0.03), 5), "lng": round(69.2890 + random.uniform(-0.03, 0.03), 5)},
    "items": [{"name": "Kapuchino", "qty": 2, "price": 25000}, {"name": "Cheesecake", "qty": 1, "price": 35000}],
    "payment": {"method": a.pay, "status": "paid"},
    "note": "Domofon ishlamaydi, qo'ng'iroq qiling",
}
req = urllib.request.Request(a.url.rstrip("/") + "/api/v1/orders", data=json.dumps(body).encode(), method="POST",
                             headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
t0 = time.time()
try:
    with urllib.request.urlopen(req, timeout=15) as r:
        print(r.status, json.dumps(json.load(r), ensure_ascii=False, indent=2), f"\n({time.time() - t0:.2f}s)")
except urllib.error.HTTPError as e:
    sys.exit(f"{e.code} {e.read().decode()}")
