import httpx
import pytest
from sqlalchemy import select

from app.config import settings
from app.models import Order, Payment, WebhookDelivery
from app.services import payments as psvc
from tests.conftest import make_restaurant, order_body

SECRET = "mc_secret"
calls: list = []


@pytest.fixture(autouse=True)
def multicard(monkeypatch):
    for k, v in dict(MULTICARD_APP_ID="app", MULTICARD_SECRET=SECRET, MULTICARD_STORE_ID="6", MULTICARD_MXIK="10101001001000000",
                     MULTICARD_PACKAGE_CODE="1500000", PUBLIC_API_URL="https://api.test").items():
        monkeypatch.setattr(settings, k, v)
    calls.clear()
    psvc._token.update(value=None, exp=0)

    def handler(req: httpx.Request):
        import json
        body = json.loads(req.content) if req.content else None
        calls.append((req.method, req.url.path, body))
        if req.url.path == "/auth":
            return httpx.Response(200, json={"success": True, "token": "tok", "expiry": "x"})
        if req.url.path == "/payment/invoice":
            n = len([c for c in calls if c[1] == "/payment/invoice"])
            return httpx.Response(200, json={"success": True, "data": {
                "uuid": f"uuid-{n}", "checkout_url": f"https://pay.test/{n}", "short_link": "https://l.test/x"}})
        if req.url.path == "/payment":
            return httpx.Response(200, json={"success": True, "data": {"uuid": "app-uuid", "checkout_url": "https://payme.test/app"}})
        return httpx.Response(404, json={"success": False})

    monkeypatch.setattr(psvc, "_transport", httpx.MockTransport(handler))


def cb(p: Payment, **kw):
    d = {"store_id": 6, "amount": p.amount * 100, "invoice_id": p.invoice_id, "billing_id": "b1", "payment_time": "2026-01-01 10:00:00",
         "card_pan": "860030******5959", "ps": "uzcard", "uuid": "tx-1", "receipt_url": "https://r.test/1"}
    d.update(kw)
    d["sign"] = psvc.make_sign(d["store_id"], d["invoice_id"], d["amount"], SECRET)
    return d


async def setup(client, db, ext="MC1", **kw):
    r = await make_restaurant(db, webhook_url="http://hook.test/in")
    h = {"Authorization": f"Bearer {r.key}"}
    res = await client.post("/api/v1/orders", json=order_body(ext, method="Multicard", status="paid", **kw), headers=h)
    assert res.status_code == 201, res.text
    return r, h, res.json()


async def test_order_with_multicard_returns_pay_url_and_waits(client, db):
    r, h, d = await setup(client, db)
    assert d["pay_status"] == "pending" and d["payment"]["pay_url"] == "https://pay.test/1"
    inv = next(c for c in calls if c[1] == "/payment/invoice")[2]
    assert inv["amount"] == d["total"] * 100 and inv["callback_url"] == "https://api.test/api/v1/payments/multicard/callback"
    assert sum(l["total"] for l in inv["ofd"]) == inv["amount"]          # fiskal qatorlar yig'indisi = summa
    assert any(l["name"] == "Yetkazib berish xizmati" for l in inv["ofd"])
    # to'lov kutilayotgan buyurtmaga kuryer berilmaydi
    o = (await db.execute(select(Order))).scalar_one()
    assert o.search_started_at is None


async def test_callback_marks_paid_and_notifies_restaurant(client, db):
    r, h, d = await setup(client, db)
    p = (await db.execute(select(Payment))).scalar_one()
    res = await client.post("/api/v1/payments/multicard/callback", json=cb(p))
    assert res.json()["success"] is True
    o = await db.get(Order, p.order_id)
    await db.refresh(o), await db.refresh(p)
    assert o.pay_status == "paid" and o.search_started_at is not None
    assert p.status == "paid" and p.card_pan.endswith("5959") and p.provider_uuid == "tx-1"
    wh = (await db.execute(select(WebhookDelivery).where(WebhookDelivery.event == "payment.paid"))).scalars().one()
    assert wh.payload["external_id"] == "MC1" and wh.payload["pay_status"] == "paid"
    st = (await client.get("/api/v1/orders/MC1/payment", headers=h)).json()
    assert st["pay_status"] == "paid" and st["payment"]["status"] == "paid"


async def test_callback_idempotent_and_double_payment_rejected(client, db):
    await setup(client, db)
    p = (await db.execute(select(Payment))).scalar_one()
    assert (await client.post("/api/v1/payments/multicard/callback", json=cb(p))).json()["success"] is True
    assert (await client.post("/api/v1/payments/multicard/callback", json=cb(p))).json()["success"] is True      # shu uuid
    again = (await client.post("/api/v1/payments/multicard/callback", json=cb(p, uuid="tx-2"))).json()
    assert again["success"] is False                                                                              # boshqa tranzaksiya -> qaytariladi


async def test_callback_bad_signature_and_wrong_amount(client, db):
    await setup(client, db)
    p = (await db.execute(select(Payment))).scalar_one()
    bad = cb(p)
    bad["sign"] = "0" * 32
    assert (await client.post("/api/v1/payments/multicard/callback", json=bad)).status_code == 403
    wrong = (await client.post("/api/v1/payments/multicard/callback", json=cb(p, amount=100))).json()
    assert wrong["success"] is False
    await db.refresh(p)
    assert p.status == "pending"


async def test_callback_after_cancel_is_rejected(client, db):
    r, h, d = await setup(client, db)
    await client.post("/api/v1/orders/MC1/cancel", json={"reason": "x"}, headers=h)
    p = (await db.execute(select(Payment))).scalar_one()
    await db.refresh(p)
    assert p.status == "cancelled"
    assert (await client.post("/api/v1/payments/multicard/callback", json=cb(p))).json()["success"] is False


async def test_pay_is_idempotent_and_renews_after_expiry(client, db):
    r, h, d = await setup(client, db)
    a = (await client.post("/api/v1/orders/MC1/pay", json={"lang": "ru"}, headers=h)).json()
    assert a["payment"]["pay_url"] == "https://pay.test/1"                      # yangi invoys yaratilmadi
    p = (await db.execute(select(Payment))).scalar_one()
    p.expires_at = p.expires_at.replace(year=2000)
    await db.commit()
    b = (await client.post("/api/v1/orders/MC1/pay", headers=h)).json()
    assert b["payment"]["pay_url"] == "https://pay.test/2" and b["payment"]["payment_id"] != a["payment"]["payment_id"]


async def test_not_configured_and_cash_order(client, db, monkeypatch):
    r = await make_restaurant(db)
    h = {"Authorization": f"Bearer {r.key}"}
    await client.post("/api/v1/orders", json=order_body("N1", method="Naqd"), headers=h)
    assert (await client.post("/api/v1/orders/N1/pay", headers=h)).status_code == 409
    monkeypatch.setattr(settings, "MULTICARD_APP_ID", "")
    res = await client.post("/api/v1/orders", json=order_body("N2", method="Multicard"), headers=h)
    assert res.status_code == 201 and res.json()["payment"] is None and "sozlanmagan" in res.json()["payment_error"]
    assert (await client.post("/api/v1/orders/N2/pay", headers=h)).status_code == 503


async def test_paid_order_cancel_marks_refund_required(client, db):
    r, h, d = await setup(client, db)
    p = (await db.execute(select(Payment))).scalar_one()
    await client.post("/api/v1/payments/multicard/callback", json=cb(p))
    await client.post("/api/v1/orders/MC1/cancel", json={"reason": "x"}, headers=h)
    await db.refresh(p)
    assert p.status == "refund_required"


async def test_payment_methods_list(client, db, monkeypatch):
    r = await make_restaurant(db)
    h = {"Authorization": f"Bearer {r.key}"}
    m = (await client.get("/api/v1/payment-methods", headers=h)).json()["methods"]
    assert [x["code"] for x in m] == ["card", "payme", "click", "uzum"] and m[0]["type"] == "card" and m[1]["type"] == "app"
    monkeypatch.setattr(settings, "MULTICARD_METHODS", "click")
    assert [x["code"] for x in (await client.get("/api/v1/payment-methods", headers=h)).json()["methods"]] == ["click"]
    monkeypatch.setattr(settings, "MULTICARD_SECRET", "")
    assert (await client.get("/api/v1/payment-methods", headers=h)).json()["methods"] == []     # sozlanmagan = bo'sh ro'yxat


async def test_app_method_uses_direct_payment_and_labels_order(client, db):
    r, h, d = await setup(client, db)
    res = (await client.post("/api/v1/orders/MC1/pay", json={"method": "payme"}, headers=h)).json()
    assert res["payment"]["method"] == "payme" and res["payment"]["pay_url"] == "https://payme.test/app"
    sent = next(c for c in calls if c[1] == "/payment")[2]
    assert sent["payment_system"] == "payme" and sent["amount"] == d["total"] * 100 and "callback_url" in sent
    p = (await db.execute(select(Payment).where(Payment.method == "payme"))).scalar_one()
    assert (await client.post("/api/v1/payments/multicard/callback", json=cb(p))).json()["success"] is True
    o = await db.get(Order, p.order_id)
    await db.refresh(o)
    assert o.pay_status == "paid" and o.pay_method == "Payme"


async def test_switching_method_cancels_previous_and_rejects_its_callback(client, db):
    r, h, d = await setup(client, db)                                  # card (avtomatik)
    await client.post("/api/v1/orders/MC1/pay", json={"method": "click"}, headers=h)
    old, new = (await db.execute(select(Payment).order_by(Payment.id))).scalars().all()
    await db.refresh(old)
    assert old.method == "card" and old.status == "cancelled" and new.method == "click" and new.status == "pending"
    assert (await client.post("/api/v1/payments/multicard/callback", json=cb(old))).json()["success"] is False


async def test_unknown_method_rejected(client, db):
    r, h, d = await setup(client, db)
    assert (await client.post("/api/v1/orders/MC1/pay", json={"method": "bitcoin"}, headers=h)).status_code == 422
    assert (await client.post("/api/v1/orders/MC1/pay", json={"method": "anorbank"}, headers=h)).status_code == 422   # yoqilmagan


async def test_order_create_with_chosen_system(client, db):
    r = await make_restaurant(db)
    h = {"Authorization": f"Bearer {r.key}"}
    b = order_body("S1", method="Multicard")
    b["payment"]["system"] = "uzum"
    res = (await client.post("/api/v1/orders", json=b, headers=h)).json()
    assert res["payment"]["method"] == "uzum" and any(c[1] == "/payment" and c[2]["payment_system"] == "uzum" for c in calls)
