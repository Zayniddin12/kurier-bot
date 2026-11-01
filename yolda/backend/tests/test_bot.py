import pytest

from app.config import settings
from app.services import dispatch
from tests.conftest import login, make_courier, make_restaurant, make_user, order_body

BOT = {"X-Bot-Key": "bot-secret"}


@pytest.fixture(autouse=True)
def _bot_key(monkeypatch):
    monkeypatch.setattr(settings, "BOT_API_KEY", "bot-secret")


async def test_bot_key_required(client, monkeypatch):
    assert (await client.get("/api/bot/state")).status_code == 401
    assert (await client.get("/api/bot/state", headers={"X-Bot-Key": "x"})).status_code == 401
    monkeypatch.setattr(settings, "BOT_API_KEY", "")
    assert (await client.get("/api/bot/state", headers=BOT)).status_code == 503


async def test_link_and_token(client, db):
    c = await make_courier(db)
    bad = await client.post("/api/bot/link", json={"telegram_id": 5, "phone": "+998901234567"}, headers=BOT)
    assert bad.status_code == 401
    ok = await client.post("/api/bot/link", json={"telegram_id": 5, "phone": "+998 " + c.phone}, headers=BOT)
    assert ok.status_code == 200 and ok.json()["courier"]["id"] == c.id
    # Telegram o'chib ketsa, yangi akkaunt shu telefon bilan qayta ulanadi (eskisi ishlamay qoladi)
    again = await client.post("/api/bot/link", json={"telegram_id": 6, "phone": c.phone}, headers=BOT)
    assert again.status_code == 200
    assert (await client.post("/api/bot/token", json={"telegram_id": 5}, headers=BOT)).status_code == 404
    t = await client.post("/api/bot/token", json={"telegram_id": 6}, headers=BOT)
    assert t.status_code == 200
    me = await client.post("/api/courier/shift/start", headers={"Authorization": "Bearer " + t.json()["access_token"]})
    assert me.status_code == 200
    assert (await client.post("/api/bot/token", json={"telegram_id": 99}, headers=BOT)).status_code == 404


async def test_link_rate_limit(client, db):
    c = await make_courier(db)
    for _ in range(5):
        r = await client.post("/api/bot/link", json={"telegram_id": 77, "phone": "000000000"}, headers=BOT)
        assert r.status_code == 401
    r = await client.post("/api/bot/link", json={"telegram_id": 77, "phone": c.phone}, headers=BOT)
    assert r.status_code == 429


async def test_order_reaches_bot_and_back(client, db):
    rest = await make_restaurant(db)
    c = await make_courier(db, telegram_id=555)
    h = {"Authorization": f"Bearer {rest.key}"}
    assert (await client.post("/api/v1/orders", json=order_body("B-1", method="Naqd"), headers=h)).status_code == 201
    await dispatch.dispatch_cycle(db)
    await db.commit()

    st = (await client.get("/api/bot/state", params={"telegram_id": 555}, headers=BOT)).json()["couriers"][0]
    assert st["order"] is None and st["offer"]["restaurant"]["name"] == "Mondi kafe"
    assert st["offer"]["collect_cash"] is True and st["has_location"] is True

    tok = (await client.post("/api/bot/token", json={"telegram_id": 555}, headers=BOT)).json()["access_token"]
    ch = {"Authorization": "Bearer " + tok}
    assert (await client.post(f"/api/courier/offers/{st['offer']['id']}/accept", headers=ch)).status_code == 200
    st = (await client.get("/api/bot/state", params={"telegram_id": 555}, headers=BOT)).json()["couriers"][0]
    o = st["order"]
    assert st["offer"] is None and o["status"] == "assigned" and o["customer"]["phone"] == "+998901234567"
    assert o["items"] == [{"name": "Kapuchino", "qty": 2}]

    await client.post(f"/api/courier/orders/{o['id']}/picked-up", headers=ch)
    assert (await client.get("/api/bot/state", params={"telegram_id": 555}, headers=BOT)).json()["couriers"][0]["order"]["status"] == "onway"
    await client.post(f"/api/courier/orders/{o['id']}/delivered", headers=ch)
    st = (await client.get("/api/bot/state", params={"telegram_id": 555}, headers=BOT)).json()["couriers"][0]
    assert st["order"] is None
    info = (await client.get(f"/api/bot/orders/{o['id']}", headers=BOT)).json()
    assert info["status"] == "delivered" and info["courier_id"] == c.id
    # restoran holatni o'z kaliti bilan ko'radi
    g = await client.get("/api/v1/orders/B-1", headers=h)
    assert g.json()["status"] == "delivered"


async def test_orders_of_any_connected_restaurant_reach_bot(client, db):
    a, b = await make_restaurant(db, "A kafe"), await make_restaurant(db, "B kafe", lat=41.37, lng=69.30)
    await make_courier(db, telegram_id=1)
    await make_courier(db, telegram_id=2)
    for r, ext in ((a, "A-1"), (b, "B-1")):
        await client.post("/api/v1/orders", json=order_body(ext), headers={"Authorization": f"Bearer {r.key}"})
    await dispatch.dispatch_cycle(db)
    await db.commit()
    cs = (await client.get("/api/bot/state", headers=BOT)).json()["couriers"]
    assert sorted(c["offer"]["restaurant"]["name"] for c in cs) == ["A kafe", "B kafe"]


async def test_connect_restaurant_with_own_key(client, db):
    await make_user(db, "op@x.uz")
    h = await login(client, "op@x.uz")
    key = "yl_live_" + "a1B2c3D4" * 4
    body = {"name": "Yangi oshxona", "lat": 41.3, "lng": 69.2, "api_key": key}
    r = await client.post("/api/admin/restaurants", json=body, headers=h)
    assert r.status_code == 201 and r.json()["api_key"] is None
    # restoran shu kalit bilan darhol buyurtma yubora oladi
    o = await client.post("/api/v1/orders", json=order_body("N-1"), headers={"Authorization": f"Bearer {key}"})
    assert o.status_code == 201
    dup = await client.post("/api/admin/restaurants", json={**body, "name": "Boshqa"}, headers=h)
    assert dup.status_code == 409
    bad = await client.post("/api/admin/restaurants", json={**body, "name": "Z", "api_key": "yl_live_short"}, headers=h)
    assert bad.status_code == 422
    gen = await client.post("/api/admin/restaurants", json={"name": "Kalitsiz", "lat": 41.3, "lng": 69.2}, headers=h)
    assert gen.status_code == 201 and gen.json()["api_key"].startswith("yl_live_")


async def test_unlink_telegram(client, db):
    await make_user(db, "op2@x.uz")
    h = await login(client, "op2@x.uz")
    c = await make_courier(db, telegram_id=9)
    r = await client.post(f"/api/admin/couriers/{c.id}/unlink-telegram", headers=h)
    assert r.status_code == 200 and r.json()["telegram_linked"] is False


async def test_route_and_customer_location_change(client, db, monkeypatch):
    from app.services import routing
    from tests.conftest import login, make_user
    monkeypatch.setattr(settings, "OSRM_URL", "")          # tarmoqsiz: to'g'ri chiziq (fallback)
    routing._cache.clear()
    rest = await make_restaurant(db)
    c = await make_courier(db, telegram_id=556, lat=41.355, lng=69.285)
    h = {"Authorization": f"Bearer {rest.key}"}
    r = await client.post("/api/v1/orders", json=order_body("L-1", method="Naqd"), headers=h)
    oid = r.json()["id"]
    await dispatch.dispatch_cycle(db)
    await db.commit()
    tok = (await client.post("/api/bot/token", json={"telegram_id": 556}, headers=BOT)).json()["access_token"]
    ch = {"Authorization": "Bearer " + tok}
    of = (await client.get("/api/bot/state", params={"telegram_id": 556}, headers=BOT)).json()["couriers"][0]["offer"]
    await client.post(f"/api/courier/offers/{of['id']}/accept", headers=ch)

    await make_user(db, "op@x.uz", "operator")
    ah = await login(client, "op@x.uz")
    rt = (await client.get(f"/api/admin/map/route/{c.id}", headers=ah)).json()
    assert rt["stage"] == "pickup" and [g["to"] for g in rt["legs"]] == ["restaurant", "customer"]
    assert rt["distance_m"] > 0 and rt["duration_s"] > 0 and rt["approx"] is True
    assert rt["legs"][0]["geometry"][0] == [41.355, 69.285]

    # ovqat olinmagan: manzil o'zgaradi, botdagi buyurtma yangi koordinata va manzilni ko'rsatadi
    ok = await client.patch(f"/api/admin/orders/{oid}/location", json={"lat": 41.40, "lng": 69.33, "address": "Yangi ko'cha 5"}, headers=ah)
    assert ok.status_code == 200 and ok.json()["lat"] == 41.40 and ok.json()["address"] == "Yangi ko'cha 5"
    st = (await client.get("/api/bot/state", params={"telegram_id": 556}, headers=BOT)).json()["couriers"][0]["order"]
    assert st["status"] == "assigned" and st["customer"]["lat"] == 41.40 and st["customer"]["address"] == "Yangi ko'cha 5"

    await client.post(f"/api/courier/orders/{oid}/picked-up", headers=ch)
    rt = (await client.get(f"/api/admin/map/route/{c.id}", headers=ah)).json()
    assert rt["stage"] == "delivering" and [g["to"] for g in rt["legs"]] == ["customer"]
    await client.patch(f"/api/admin/orders/{oid}/location", json={"lat": 41.41, "lng": 69.34}, headers=ah)
    st = (await client.get("/api/bot/state", params={"telegram_id": 556}, headers=BOT)).json()["couriers"][0]["order"]
    assert st["status"] == "onway" and (st["customer"]["lat"], st["customer"]["lng"]) == (41.41, 69.34)

    bad = await client.patch(f"/api/admin/orders/{oid}/location", json={"lat": 100, "lng": 69.3}, headers=ah)
    assert bad.status_code == 422
    await client.post(f"/api/courier/orders/{oid}/delivered", headers=ch)
    done = await client.patch(f"/api/admin/orders/{oid}/location", json={"lat": 41.4, "lng": 69.3}, headers=ah)
    assert done.status_code == 409


async def test_osrm_route_parsing_and_fallback(monkeypatch):
    from app.services import routing

    class Resp:
        def __init__(self, ok): self.ok = ok
        def raise_for_status(self):
            if not self.ok: raise RuntimeError("503")
        def json(self):
            return {"routes": [{"distance": 1234.4, "geometry": {"coordinates": [[69.29, 41.36], [69.30, 41.37]]}}]}

    class Client:
        ok = True
        async def get(self, *a, **k): return Resp(Client.ok)

    monkeypatch.setattr(settings, "OSRM_URL", "http://osrm")
    monkeypatch.setattr(routing, "_client", Client())
    routing._cache.clear()
    g = await routing.leg((41.36, 69.29), (41.37, 69.30))
    assert g["distance_m"] == 1234 and g["approx"] is False and g["geometry"][0] == [41.36, 69.29]
    Client.ok = False                                           # OSRM ishlamasa — to'g'ri chiziq
    routing._cache.clear()
    g = await routing.leg((41.36, 69.29), (41.37, 69.30))
    assert g["approx"] is True and g["distance_m"] > 1000
