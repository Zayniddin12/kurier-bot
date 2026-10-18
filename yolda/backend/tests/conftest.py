import os

os.environ["DATABASE_URL"] = os.getenv("TEST_DATABASE_URL", "postgresql+asyncpg://yolda:yolda@localhost:5432/yolda_test")
os.environ["RUN_WORKERS"] = "false"
os.environ["DEMO_SIMULATION"] = "false"

import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.db import Base, SessionLocal, engine  # noqa: E402
import app.models  # noqa: E402,F401
from app.main import app  # noqa: E402
from app.models import Courier, Restaurant, User  # noqa: E402
from app.security import hash_password, new_api_key  # noqa: E402


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _schema():
    async with engine.begin() as c:
        await c.run_sync(Base.metadata.drop_all)
        await c.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def _clean(_schema):
    async with engine.begin() as c:
        await c.execute(text("TRUNCATE webhook_deliveries, dismissed_alerts, complaints, feed_events, ledger_entries, "
                             "order_issues, order_offers, order_items, orders, couriers, users, restaurants "
                             "RESTART IDENTITY CASCADE"))
        await c.execute(text("ALTER SEQUENCE orders_id_seq RESTART WITH 118401"))
    yield


@pytest_asyncio.fixture
async def db():
    async with SessionLocal() as s:
        yield s


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def make_restaurant(db, name="Mondi kafe", lat=41.36, lng=69.29, status="open", webhook_url=None):
    key, prefix, h = new_api_key()
    r = Restaurant(name=name, lat=lat, lng=lng, status=status, api_key_prefix=prefix, api_key_hash=h, prep_minutes=16,
                   district="Yunusobod", webhook_url=webhook_url, webhook_secret="whsec_test" if webhook_url else None)
    db.add(r)
    await db.commit()
    r.key = key
    return r


_n = [0]


async def make_courier(db, lat=41.36, lng=69.29, status="idle", vehicle="Skuter", balance=0, **kw):
    _n[0] += 1
    c = Courier(number=100 + _n[0], first_name="Test", last_name=f"Kuryer{_n[0]}", phone=f"90{_n[0]:07d}",
                pinfl=f"{_n[0]:014d}", vehicle=vehicle, lat=lat, lng=lng, work_status=status, balance=balance, **kw)
    db.add(c)
    await db.commit()
    return c


async def make_user(db, email, role="operator", restaurant_id=None, password="pw123456"):
    u = User(email=email, password_hash=hash_password(password), full_name=email, role=role, restaurant_id=restaurant_id)
    db.add(u)
    await db.commit()
    return u


async def login(client, email, password="pw123456"):
    r = await client.post("/api/admin/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["access_token"]}


def order_body(ext="X-1", method="Payme", status="paid", lat=41.37, lng=69.30, items=None):
    b = {"external_id": ext, "customer": {"name": "Test", "phone": "+998901234567"},
         "address": {"text": "Manzil", "district": "Yunusobod", "lat": lat, "lng": lng},
         "items": items or [{"name": "Kapuchino", "qty": 2, "price": 25000}],
         "payment": {"method": method, "status": status}}
    if lat is None:
        b["address"].pop("lat"), b["address"].pop("lng")
    return b
