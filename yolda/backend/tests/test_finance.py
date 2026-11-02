from datetime import datetime, timezone

from app.models import VendorLedgerEntry
from tests.conftest import login, make_courier, make_restaurant, make_user


async def test_courier_finance_list_filters_and_balance(client, db):
    await make_user(db, "op@x.uz", "operator")
    h = await login(client, "op@x.uz")
    c = await make_courier(db)
    await client.post(f"/api/admin/couriers/{c.id}/ledger", json={"type": "topup", "amount": 80000}, headers=h)
    await client.post(f"/api/admin/couriers/{c.id}/ledger", json={"type": "payout", "amount": 50000, "note": "Maosh"}, headers=h)
    r = (await client.get("/api/admin/finance/couriers", headers=h)).json()
    assert r["total"] == 2
    assert r["summary"] == {"income": 80000, "expense": 50000, "balance": 30000}
    assert [i["balance_after"] for i in r["items"]] == [30000, 80000]      # yangi yozuv birinchi
    assert r["items"][0]["kind"] == "expense" and r["items"][0]["reason"] == "payout"
    only = (await client.get("/api/admin/finance/couriers?kind=income", headers=h)).json()
    assert only["total"] == 1 and only["summary"]["expense"] == 0
    assert (await client.get("/api/admin/finance/couriers?reason=payout&desc=maosh", headers=h)).json()["total"] == 1
    assert (await client.get("/api/admin/finance/couriers?q=zzz", headers=h)).json()["total"] == 0
    assert (await client.get("/api/admin/finance/couriers?from=2999-01-01", headers=h)).json()["total"] == 0


async def test_vendor_finance_list_and_staff_forbidden(client, db):
    rest = await make_restaurant(db, "Bellissimo")
    await make_user(db, "op@x.uz", "operator")
    await make_user(db, "st@x.uz", "restaurant_staff", rest.id)
    now = datetime.now(timezone.utc)
    db.add_all([VendorLedgerEntry(restaurant_id=rest.id, type="payment", amount=120000, note="Naqdsiz to'lov uchun o'tkazma", order_id=5, created_at=now),
                VendorLedgerEntry(restaurant_id=rest.id, type="commission", amount=-13500, note="Buyurtma uchun 15% komissiya", created_at=now)])
    await db.commit()
    h = await login(client, "op@x.uz")
    r = (await client.get("/api/admin/finance/vendors", headers=h)).json()
    assert r["total"] == 2 and r["summary"] == {"income": 120000, "expense": 13500, "balance": 106500}
    assert {i["balance_after"] for i in r["items"]} == {120000, 106500}
    assert r["items"][-1]["description"].endswith("Buyurtma raqami: 5") and r["items"][0]["creator"] == "Tizim"
    assert (await client.get("/api/admin/finance/vendors?type=commission&kind=expense&q=bell", headers=h)).json()["total"] == 1
    assert (await client.get("/api/admin/finance/vendors?creator=system", headers=h)).json()["total"] == 2
    hs = await login(client, "st@x.uz")
    assert (await client.get("/api/admin/finance/vendors", headers=hs)).status_code == 403
    assert (await client.get("/api/admin/finance/couriers", headers=hs)).status_code == 403
