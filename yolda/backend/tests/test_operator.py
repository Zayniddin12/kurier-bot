from sqlalchemy import select

from app.models import Courier, Order
from app.services.orders import create_order
from tests.conftest import login, make_courier, make_restaurant, make_user, order_body


async def _order(db, r, ext="A", method="Payme", status="paid", phone="+998901112233"):
    o, _ = await create_order(db, r, external_id=ext, customer_name="Mijoz", customer_phone=phone, address="Manzil",
                              lat=41.37, lng=69.30, items=[{"name": "Osh", "qty": 2, "price": 25000}],
                              pay_method=method, pay_status=status)
    await db.commit()
    return o


async def _h(client, db, role="operator"):
    await make_user(db, f"{role}@x.uz", role)
    return await login(client, f"{role}@x.uz")


async def test_queue_counts_and_filters(client, db):
    h = await _h(client, db)
    r = await make_restaurant(db)
    c = await make_courier(db)
    o1 = await _order(db, r, "A")
    await _order(db, r, "B")
    q = (await client.get("/api/admin/operator/queue", headers=h)).json()
    assert q["counts"]["active"] == 2 and q["counts"]["nocourier"] == 2 and q["counts"]["new"] == 2
    assert q["counts"]["idle_couriers"] == 1 and q["total"] == 2
    a = await client.post(f"/api/admin/operator/orders/{o1.id}/assign", json={"courier_id": c.id}, headers=h)
    assert a.status_code == 200 and a.json()["status"] == "assigned" and a.json()["courier"]["id"] == c.id
    q = (await client.get("/api/admin/operator/queue", params={"chip": "assigned"}, headers=h)).json()
    assert [x["id"] for x in q["items"]] == [o1.id]
    q = (await client.get("/api/admin/operator/queue", params={"chip": "nocourier"}, headers=h)).json()
    assert q["total"] == 1
    q = (await client.get("/api/admin/operator/queue", params={"courier_id": c.id}, headers=h)).json()
    assert q["counts"]["active"] == 1
    s = (await client.get("/api/admin/operator/queue", params={"q": "Mijoz"}, headers=h)).json()
    assert s["total"] == 2


async def test_staff_forbidden(client, db):
    r = await make_restaurant(db)
    await make_user(db, "s@x.uz", "restaurant_staff", restaurant_id=r.id)
    h = await login(client, "s@x.uz")
    assert (await client.get("/api/admin/operator/queue", headers=h)).status_code == 403


async def test_assign_replace_unassign_and_advance(client, db):
    h = await _h(client, db)
    r = await make_restaurant(db)
    c1, c2 = await make_courier(db), await make_courier(db, lat=41.365)
    o = await _order(db, r, "A", method="Naqd")
    base = f"/api/admin/operator/orders/{o.id}"
    cand = (await client.get(base + "/couriers", headers=h)).json()
    assert {x["id"] for x in cand} == {c1.id, c2.id} and cand[0]["dist_km"] <= cand[1]["dist_km"]
    d = (await client.get(base, headers=h)).json()
    assert d["next_action"]["kind"] == "assign" and d["customer"]["delivered"] == 0
    assert (await client.post(base + "/advance", headers=h)).status_code == 409
    assert (await client.post(base + "/assign", json={"courier_id": c1.id}, headers=h)).status_code == 200
    # almashtirish: eski kuryer bo'shaydi
    d = (await client.post(base + "/assign", json={"courier_id": c2.id}, headers=h)).json()
    assert d["courier"]["id"] == c2.id
    await db.refresh(c1), await db.refresh(c2)
    assert c1.current_order_id is None and c1.work_status == "idle" and c2.current_order_id == o.id
    assert (await client.post(base + "/assign", json={"courier_id": c2.id}, headers=h)).status_code == 409
    # olib tashlash
    d = (await client.post(base + "/unassign", headers=h)).json()
    assert d["status"] == "new" and d["courier"] is None
    await db.refresh(c2)
    assert c2.current_order_id is None
    # qayta biriktirish -> olib ketdi -> yetkazildi
    await client.post(base + "/assign", json={"courier_id": c1.id}, headers=h)
    d = (await client.post(base + "/advance", headers=h)).json()
    assert d["status"] == "onway" and d["next_action"]["kind"] == "delivered"
    d = (await client.post(base + "/advance", headers=h)).json()
    assert d["status"] == "delivered" and d["next_action"] is None and not d["can_edit"]
    assert any("Yetkazildi" in s["label"] for s in d["op_timeline"])
    assert len(d["logs"]) >= 5 and len(d["payments"]) >= 2
    assert (await client.post(base + "/assign", json={"courier_id": c2.id}, headers=h)).status_code == 409


async def test_assign_busy_courier_goes_to_queue(client, db):
    h = await _h(client, db)
    r = await make_restaurant(db)
    c = await make_courier(db)
    o1, o2 = await _order(db, r, "A"), await _order(db, r, "B")
    await client.post(f"/api/admin/operator/orders/{o1.id}/assign", json={"courier_id": c.id}, headers=h)
    d = (await client.post(f"/api/admin/operator/orders/{o2.id}/assign", json={"courier_id": c.id}, headers=h)).json()
    assert d["queued"] is True and d["status"] == "assigned"
    await db.refresh(c)
    assert c.current_order_id == o1.id


async def test_pending_payment_confirm_notes_and_block(client, db):
    h = await _h(client, db)
    r = await make_restaurant(db)
    o = await _order(db, r, "P", status="pending", phone="+998901234567")
    base = f"/api/admin/operator/orders/{o.id}"
    d = (await client.get(base, headers=h)).json()
    assert d["next_action"]["kind"] == "confirm_payment"
    d = (await client.post(base + "/advance", headers=h)).json()
    assert d["pay_status"] == "paid" and d["next_action"]["kind"] == "assign"
    d = (await client.patch(base + "/notes", json={"restaurant_note": "Achchiq qilmang", "courier_note": "Qo'ng'iroq qiling"}, headers=h)).json()
    assert d["restaurant_note"] == "Achchiq qilmang" and d["courier_note"] == "Qo'ng'iroq qiling"
    d = (await client.post(base + "/customer-notes", json={"text": "Doim kech oladi"}, headers=h)).json()
    assert d["customer"]["notes"][0]["text"] == "Doim kech oladi"
    d = (await client.post(base + "/block-customer", json={"reason": "spam"}, headers=h)).json()
    assert d["customer"]["blocked"] is True
    ik = {"Authorization": f"Bearer {r.key}"}
    blocked = await client.post("/api/v1/orders", json=order_body("NEW-1"), headers=ik)
    assert blocked.status_code == 403
    d = (await client.post(base + "/unblock-customer", headers=h)).json()
    assert d["customer"]["blocked"] is False
    assert (await client.post("/api/v1/orders", json=order_body("NEW-2"), headers=ik)).status_code == 201


async def test_order_route_without_courier(client, db):
    h = await _h(client, db)
    r = await make_restaurant(db)
    o = await _order(db, r)
    d = (await client.get(f"/api/admin/operator/orders/{o.id}/route", headers=h)).json()
    assert len(d["legs"]) == 1 and d["legs"][0]["to"] == "customer"


async def test_operator_creates_cash_order_from_static_menu(client, db):
    h = await _h(client, db)
    r = await make_restaurant(db)
    menu = (await client.get(f"/api/admin/operator/restaurants/{r.id}/menu", headers=h)).json()["items"]
    assert menu and {"id", "name", "price"} <= set(menu[0])
    q = (await client.get("/api/admin/operator/quote", params={"restaurant_id": r.id, "lat": 41.37, "lng": 69.30}, headers=h)).json()
    assert q["delivery_fee"] > 0
    body = {"restaurant_id": r.id, "customer_name": "Ali", "customer_phone": "+998901234567", "address": "Test ko'chasi 1",
            "lat": 41.37, "lng": 69.30, "items": [{"menu_id": menu[0]["id"], "qty": 2}], "note": "Achchiq bo'lmasin",
            "courier_note": "Qo'ng'iroq qiling"}
    res = await client.post("/api/admin/operator/orders", json=body, headers=h)
    assert res.status_code == 201, res.text
    o = (await db.execute(select(Order).order_by(Order.id.desc()))).scalars().first()
    assert o.pay_method == "Naqd" and o.pay_status == "cod" and o.external_id.startswith("OP-")
    assert o.subtotal == 2 * menu[0]["price"] and o.total == o.subtotal + o.delivery_fee
    assert o.courier_note == "Qo'ng'iroq qiling" and o.note == "Achchiq bo'lmasin"
    bad = await client.post("/api/admin/operator/orders", json={**body, "items": [{"menu_id": 9999, "qty": 1}]}, headers=h)
    assert bad.status_code == 422
    nofee = await client.post("/api/admin/operator/orders", json={**body, "lat": None, "lng": None}, headers=h)
    assert nofee.status_code == 422
