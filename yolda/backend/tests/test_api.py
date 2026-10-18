from sqlalchemy import func, select

from app.models import Courier, Order
from tests.conftest import login, make_courier, make_restaurant, make_user, order_body


async def test_idempotent_order_and_responses(client, db):
    r = await make_restaurant(db)
    h = {"Authorization": f"Bearer {r.key}"}
    a = await client.post("/api/v1/orders", json=order_body("MND-1"), headers=h)
    b = await client.post("/api/v1/orders", json=order_body("MND-1"), headers=h)
    assert a.status_code == 201 and b.status_code == 200
    assert a.json()["id"] == b.json()["id"] == 118401
    assert a.json()["subtotal"] == 50000 and a.json()["total"] == 50000 + a.json()["delivery_fee"]
    assert (await db.execute(select(func.count()).select_from(Order))).scalar_one() == 1
    g = await client.get("/api/v1/orders/MND-1", headers=h)
    assert g.json()["status"] == "new" and g.json()["courier"] is None


async def test_integration_auth_paused_fee_and_cancel(client, db):
    r = await make_restaurant(db)
    h = {"Authorization": f"Bearer {r.key}"}
    assert (await client.post("/api/v1/orders", json=order_body(), headers={"Authorization": "Bearer nope"})).status_code == 401
    no_geo = await client.post("/api/v1/orders", json=order_body("NG", lat=None, lng=None), headers=h)
    assert no_geo.status_code == 422 and "detail" in no_geo.json()
    body = order_body("NG2", lat=None, lng=None)
    body["delivery_fee"] = 10000
    ok = await client.post("/api/v1/orders", json=body, headers=h)
    assert ok.status_code == 201 and ok.json()["delivery_fee"] == 10000 and ok.json()["distance_km"] is None
    c = await client.post("/api/v1/orders/NG2/cancel", json={"reason": "x"}, headers=h)
    assert c.status_code == 200 and c.json()["status"] == "cancelled"
    again = await client.post("/api/v1/orders/NG2/cancel", json={"reason": "x"}, headers=h)
    assert again.status_code == 409
    p = await client.post("/api/v1/restaurant/status", json={"status": "paused", "reason": "yopiq"}, headers=h)
    assert p.status_code == 200
    blocked = await client.post("/api/v1/orders", json=order_body("NEW-1"), headers=h)
    assert blocked.status_code == 409 and blocked.json()["detail"] == "Restoran hozir buyurtma qabul qilmayapti"
    same = await client.post("/api/v1/orders", json=order_body("NG2"), headers=h)       # idempotent mavjud — pauzada ham qaytadi
    assert same.status_code == 200


async def test_payment_flow(client, db):
    r = await make_restaurant(db)
    h = {"Authorization": f"Bearer {r.key}"}
    await client.post("/api/v1/orders", json=order_body("PP", status="pending"), headers=h)
    f = await client.post("/api/v1/orders/PP/payment", json={"status": "failed"}, headers=h)
    assert f.json()["status"] == "cancelled" and f.json()["pay_status"] == "failed"
    await client.post("/api/v1/orders", json=order_body("P2", status="pending"), headers=h)
    ok = await client.post("/api/v1/orders/P2/payment", json={"status": "paid"}, headers=h)
    assert ok.json()["pay_status"] == "paid" and ok.json()["status"] == "new"
    again = await client.post("/api/v1/orders/P2/payment", json={"status": "paid"}, headers=h)
    assert again.status_code == 409


async def test_restaurant_staff_isolation(client, db):
    a = await make_restaurant(db, "A")
    b = await make_restaurant(db, "B")
    await client.post("/api/v1/orders", json=order_body("A1"), headers={"Authorization": f"Bearer {a.key}"})
    await client.post("/api/v1/orders", json=order_body("B1"), headers={"Authorization": f"Bearer {b.key}"})
    await make_user(db, "a@x.uz", "restaurant_staff", a.id)
    await make_user(db, "op@x.uz", "operator")
    ha, ho = await login(client, "a@x.uz"), await login(client, "op@x.uz")
    # boshqa restoranni so'rasa ham — faqat o'ziniki
    r = await client.get(f"/api/admin/orders?restaurant_id={b.id}", headers=ha)
    assert r.json()["total"] == 1 and r.json()["items"][0]["restaurant"]["id"] == a.id
    assert (await client.get("/api/admin/orders", headers=ho)).json()["total"] == 2
    assert (await client.get("/api/admin/orders/118402", headers=ha)).status_code == 404
    assert (await client.get(f"/api/admin/restaurants/{b.id}", headers=ha)).status_code == 404
    assert len((await client.get("/api/admin/restaurants", headers=ha)).json()["items"]) == 1
    assert (await client.get(f"/api/admin/overview?restaurant_id={b.id}&period=month", headers=ha)).json()["kpis"]["orders"]["value"] == 1
    assert (await client.get("/api/admin/couriers", headers=ha)).status_code == 403
    assert (await client.get("/api/admin/reports/salary", headers=ha)).status_code == 403
    assert (await client.post("/api/admin/restaurants", headers=ha, json={"name": "Z", "lat": 1, "lng": 1})).status_code == 403
    assert (await client.get("/api/admin/orders")).status_code == 401


async def test_courier_validation_block_and_ledger(client, db):
    await make_user(db, "op@x.uz", "operator")
    h = await login(client, "op@x.uz")
    base = {"first_name": "Ali", "last_name": "Vali", "phone": "90 123 45 67", "pinfl": "12345678901234", "vehicle": "Skuter"}
    bad = await client.post("/api/admin/couriers", json={**base, "first_name": ""}, headers=h)
    assert bad.status_code == 422 and bad.json()["detail"] == "Ism va familiyani kiriting"
    assert (await client.post("/api/admin/couriers", json={**base, "phone": "123"}, headers=h)).json()["detail"] == "Telefon raqami 9 ta raqamdan iborat bo'lsin"
    assert (await client.post("/api/admin/couriers", json={**base, "pinfl": "123"}, headers=h)).json()["detail"] == "JShShIR 14 ta raqamdan iborat bo'lsin"
    ok = await client.post("/api/admin/couriers", json=base, headers=h)
    assert ok.status_code == 201 and ok.json()["work_status"] == "offline" and ok.json()["balance"] == 0 and ok.json()["rating"] == 5.0
    dup = await client.post("/api/admin/couriers", json=base, headers=h)
    assert dup.json()["detail"] == "Bu JShShIR bilan kuryer allaqachon bor"
    cid = ok.json()["id"]
    pay = await client.post(f"/api/admin/couriers/{cid}/ledger", json={"type": "payout", "amount": 50000}, headers=h)
    assert pay.json()["entry"]["amount"] == -50000 and pay.json()["courier"]["balance"] == -50000
    top = await client.post(f"/api/admin/couriers/{cid}/ledger", json={"type": "topup", "amount": 80000}, headers=h)
    assert top.json()["courier"]["balance"] == 30000
    assert (await client.post(f"/api/admin/couriers/{cid}/ledger", json={"type": "topup", "amount": 0}, headers=h)).status_code == 422
    # faol buyurtmali kuryerni bloklab bo'lmaydi
    busy = await make_courier(db, status="pickup")
    busy.current_order_id = 999
    await db.commit()
    blk = await client.post(f"/api/admin/couriers/{busy.id}/block", headers=h)
    assert blk.status_code == 409 and "faol buyurtma" in blk.json()["detail"]
    free = await client.post(f"/api/admin/couriers/{cid}/block", headers=h)
    assert free.json()["account_status"] == "blocked" and free.json()["work_status"] == "offline"


async def test_salary_settle_and_cancel_refund(client, db):
    r = await make_restaurant(db)
    h = {"Authorization": f"Bearer {r.key}"}
    await make_user(db, "op@x.uz", "operator")
    ho = await login(client, "op@x.uz")
    await client.post("/api/v1/orders", json=order_body("C1"), headers=h)
    res = await client.post("/api/admin/orders/118401/cancel", json={"reason": "Mijoz bekor qildi"}, headers=ho)
    assert res.json()["refunded"] is True and res.json()["order"]["pay_status"] == "refunded"
    await client.post("/api/v1/orders", json=order_body("C2", method="Naqd"), headers=h)
    res = await client.post("/api/admin/orders/118402/cancel", json={"reason": "x"}, headers=ho)
    assert res.json()["order"]["pay_status"] == "void"
    c = await make_courier(db, balance=100_000)
    s = await client.get("/api/admin/reports/salary", headers=ho)
    item = next(i for i in s.json()["items"] if i["courier"]["id"] == c.id)
    assert item["payable"] == 100_000
    st = await client.post(f"/api/admin/couriers/{c.id}/settle", headers=ho)
    assert st.json()["paid"] == 100_000 and st.json()["courier"]["balance"] == 0
