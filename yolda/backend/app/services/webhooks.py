import asyncio
import hashlib
import hmac
import json
import logging
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import select

from app.config import ORDER_STATUS
from app.db import SessionLocal
from app.models import Restaurant, WebhookDelivery

log = logging.getLogger("yolda.webhooks")
RETRY_DELAYS = [10, 60, 300]  # sekund; 1 ta asosiy + 3 ta qayta urinish


def sign(secret: str, body: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def build_payload(order, courier) -> dict:
    return {
        "event": "order.status_changed", "external_id": order.external_id, "status": order.status,
        "status_text": ORDER_STATUS[order.status][0],
        "courier": {"name": f"{courier.first_name} {courier.last_name}", "phone": courier.phone} if courier else None,
        "at": datetime.now(timezone.utc).isoformat(),
    }


def queue(db, order, restaurant: Restaurant, courier):
    if not restaurant.webhook_url:
        return
    db.add(WebhookDelivery(restaurant_id=restaurant.id, order_id=order.id, event="order.status_changed",
                           payload=build_payload(order, courier), attempts=0,
                           next_retry_at=datetime.now(timezone.utc)))


async def deliver_pending(client: httpx.AsyncClient | None = None):
    now = datetime.now(timezone.utc)
    async with SessionLocal() as db:
        rows = (await db.execute(select(WebhookDelivery).where(
            WebhookDelivery.delivered_at.is_(None), WebhookDelivery.next_retry_at <= now,
            WebhookDelivery.attempts < len(RETRY_DELAYS) + 1).limit(50))).scalars().all()
        for d in rows:
            r = await db.get(Restaurant, d.restaurant_id)
            if not r or not r.webhook_url:
                d.next_retry_at = None
                continue
            body = json.dumps(d.payload, ensure_ascii=False, separators=(",", ":")).encode()
            headers = {"Content-Type": "application/json",
                       "X-Yolda-Signature": sign(r.webhook_secret or "", body)}
            code = None
            try:
                async with (client or httpx.AsyncClient(timeout=8)) as c:
                    resp = await c.post(r.webhook_url, content=body, headers=headers)
                    code = resp.status_code
            except Exception as e:  # noqa
                log.warning("webhook xato: %s", e)
            d.attempts += 1
            d.status_code = code
            if code is not None and 200 <= code < 300:
                d.delivered_at = datetime.now(timezone.utc)
                d.next_retry_at = None
            elif d.attempts <= len(RETRY_DELAYS):
                d.next_retry_at = datetime.now(timezone.utc) + timedelta(seconds=RETRY_DELAYS[d.attempts - 1])
            else:
                d.next_retry_at = None
        await db.commit()
        return len(rows)
