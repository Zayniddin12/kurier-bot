import json

import httpx
from sqlalchemy import select

from app.models import WebhookDelivery
from app.services import webhooks
from tests.conftest import make_restaurant, order_body


async def test_webhook_signature_and_retry(client, db):
    r = await make_restaurant(db, webhook_url="http://hook.test/in")
    h = {"Authorization": f"Bearer {r.key}"}
    await client.post("/api/v1/orders", json=order_body("W1"), headers=h)
    await client.post("/api/v1/orders/W1/cancel", json={"reason": "x"}, headers=h)   # status o'zgardi -> webhook navbatda
    d = (await db.execute(select(WebhookDelivery))).scalars().one()
    assert d.payload["event"] == "order.status_changed" and d.payload["status"] == "cancelled"

    seen = {}

    def handler(req: httpx.Request):
        seen["sig"], seen["body"] = req.headers["X-Yolda-Signature"], req.content
        return httpx.Response(500)

    await webhooks.deliver_pending(httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    assert seen["sig"] == webhooks.sign("whsec_test", seen["body"])
    assert json.loads(seen["body"])["external_id"] == "W1"
    await db.refresh(d)
    assert d.attempts == 1 and d.status_code == 500 and d.delivered_at is None and d.next_retry_at is not None

    d.next_retry_at = d.next_retry_at.replace(year=2000)
    await db.commit()
    await webhooks.deliver_pending(httpx.AsyncClient(transport=httpx.MockTransport(lambda q: httpx.Response(200))))
    await db.refresh(d)
    assert d.attempts == 2 and d.delivered_at is not None
