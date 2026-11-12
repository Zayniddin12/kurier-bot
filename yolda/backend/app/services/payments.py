"""Multicard (Rahmat) to'lov shlyuzi: invoys yaratish, callback imzosini tekshirish, to'lovni tasdiqlash.

Hujjat: https://docs.multicard.uz  (invoys: POST /payment/invoice, callback: imzo = md5(store_id+invoice_id+amount+secret)).
Pul Tez-yetkaz kassasiga (store_id) tushadi; restoranlar bilan hisob-kitob vendor ledger orqali.
"""
import hashlib
import hmac
import logging
import time
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import select

from app.config import settings
from app.models import Order, OrderItem, Payment, Restaurant
from app.services import orders as osvc
from app.services import webhooks
from app.services.events import feed

log = logging.getLogger("yolda.payments")

_transport: httpx.AsyncBaseTransport | None = None   # testlarda MockTransport qo'yiladi
_token: dict = {"value": None, "exp": 0.0}


# Mijozga ko'rsatiladigan usullar. card = Multicard to'lov sahifasi (Uzcard/Humo/Visa/Mastercard), qolganlari — ilovaga yo'naltirish
METHODS = {
    "card": {"name": "Karta (Uzcard, Humo, Visa, Mastercard)", "type": "card", "label": "Karta"},
    "payme": {"name": "Payme", "type": "app", "label": "Payme"},
    "click": {"name": "Click", "type": "app", "label": "Click"},
    "uzum": {"name": "Uzum Bank", "type": "app", "label": "Uzum"},
    "anorbank": {"name": "Anorbank", "type": "app", "label": "Anorbank"},
    "alif": {"name": "Alif", "type": "app", "label": "Alif"},
    "oson": {"name": "Oson", "type": "app", "label": "Oson"},
    "xazna": {"name": "Xazna", "type": "app", "label": "Xazna"},
    "beepul": {"name": "Beepul", "type": "app", "label": "Beepul"},
    "trastpay": {"name": "Trastpay", "type": "app", "label": "Trastpay"},
}


def enabled_methods() -> list[dict]:
    codes = [c.strip() for c in settings.MULTICARD_METHODS.split(",") if c.strip() in METHODS]
    return [{"code": c, "name": METHODS[c]["name"], "type": METHODS[c]["type"]} for c in codes] if configured() else []


class PaymentError(Exception):
    def __init__(self, message: str, status: int = 502):
        self.message, self.status = message, status


def configured() -> bool:
    s = settings
    return bool(s.MULTICARD_APP_ID and s.MULTICARD_SECRET and s.MULTICARD_STORE_ID and s.MULTICARD_MXIK
                and s.MULTICARD_PACKAGE_CODE and s.PUBLIC_API_URL)


def callback_url() -> str:
    return settings.PUBLIC_API_URL.rstrip("/") + "/api/v1/payments/multicard/callback"


def make_sign(store_id, invoice_id, amount, secret: str) -> str:
    return hashlib.md5(f"{store_id}{invoice_id}{amount}{secret}".encode()).hexdigest()


def verify_sign(data: dict) -> bool:
    got = str(data.get("sign") or "").lower()
    try:
        amount = int(float(data.get("amount")))
    except (TypeError, ValueError):
        return False
    want = make_sign(data.get("store_id"), data.get("invoice_id"), amount, settings.MULTICARD_SECRET)
    return bool(got) and hmac.compare_digest(got, want)


async def _call(method: str, path: str, json: dict | None = None, *, auth: bool = True, _retry: bool = True) -> dict:
    headers = {}
    if auth:
        headers["Authorization"] = "Bearer " + await _get_token()
    try:
        async with httpx.AsyncClient(base_url=settings.MULTICARD_BASE_URL.rstrip("/"), timeout=15,
                                     transport=_transport) as c:
            resp = await c.request(method, path, json=json, headers=headers)
    except httpx.HTTPError as e:
        raise PaymentError(f"Multicard bilan aloqa yo'q: {e.__class__.__name__}")
    if resp.status_code == 401 and auth and _retry:
        _token["value"] = None
        return await _call(method, path, json, auth=auth, _retry=False)
    try:
        body = resp.json()
    except ValueError:
        raise PaymentError(f"Multicard noto'g'ri javob berdi (HTTP {resp.status_code})")
    if resp.status_code >= 400 or body.get("success") is False:
        err = body.get("error") or {}
        log.warning("Multicard xato %s %s: %s", method, path, body)
        raise PaymentError(f"Multicard: {err.get('details') or err.get('code') or resp.status_code}")
    return body


async def _get_token() -> str:
    if _token["value"] and _token["exp"] > time.monotonic():
        return _token["value"]
    body = await _call("POST", "/auth", {"application_id": settings.MULTICARD_APP_ID, "secret": settings.MULTICARD_SECRET},
                       auth=False)
    d = body.get("data") if isinstance(body.get("data"), dict) else body
    tok = d.get("token")
    if not tok:
        raise PaymentError("Multicard token bermadi")
    _token["value"], _token["exp"] = tok, time.monotonic() + 23 * 3600   # token 24 soat amal qiladi
    return tok


def _ofd(o: Order, items: list[OrderItem]) -> list[dict]:
    s = settings
    lines = [{"qty": i.qty, "price": i.price * 100, "total": i.qty * i.price * 100, "mxik": s.MULTICARD_MXIK,
              "package_code": s.MULTICARD_PACKAGE_CODE, "name": i.name} for i in items]
    if o.delivery_fee:
        lines.append({"qty": 1, "price": o.delivery_fee * 100, "total": o.delivery_fee * 100,
                      "mxik": s.MULTICARD_DELIVERY_MXIK or s.MULTICARD_MXIK,
                      "package_code": s.MULTICARD_DELIVERY_PACKAGE_CODE or s.MULTICARD_PACKAGE_CODE,
                      "name": "Yetkazib berish xizmati"})
    return lines


async def active_payment(db, o: Order) -> Payment | None:
    now = datetime.now(timezone.utc)
    p = (await db.execute(select(Payment).where(Payment.order_id == o.id, Payment.status == "pending")
                          .order_by(Payment.id.desc()))).scalars().first()
    if p and p.expires_at and p.expires_at <= now:
        p.status = "expired"
        return None
    return p


async def create_payment(db, o: Order, *, method="card", return_url=None, return_error_url=None, lang="uz") -> Payment:
    """Tanlangan usul bilan to'lov havolasini yaratadi. Idempotent: shu usulda faol havola bo'lsa — o'sha qaytadi;
    mijoz usulni almashtirsa, eskisi bekor bo'lib yangisi yaratiladi."""
    if not configured():
        raise PaymentError("To'lov tizimi sozlanmagan", 503)
    if method not in {m["code"] for m in enabled_methods()}:
        raise PaymentError(f"To'lov usuli mavjud emas: {method}", 422)
    if o.status == "cancelled":
        raise PaymentError("Buyurtma bekor qilingan", 409)
    if o.pay_status != "pending":
        raise PaymentError("Bu buyurtma uchun to'lov kerak emas yoki allaqachon to'langan", 409)
    if (p := await active_payment(db, o)):
        if p.method == method:
            return p
        p.status = "cancelled"      # usul almashdi; eski havola orqali to'lov kelsa — callback rad etiladi va pul qaytariladi
    n = (await db.execute(select(Payment).where(Payment.order_id == o.id))).scalars().all()
    items = (await db.execute(select(OrderItem).where(OrderItem.order_id == o.id).order_by(OrderItem.id))).scalars().all()
    p = Payment(order_id=o.id, restaurant_id=o.restaurant_id, method=method, invoice_id=f"YL{o.id}-{len(n) + 1}", amount=o.total,
                status="pending", expires_at=datetime.now(timezone.utc) + timedelta(seconds=settings.MULTICARD_INVOICE_TTL))
    payload = {"store_id": int(settings.MULTICARD_STORE_ID) if settings.MULTICARD_STORE_ID.isdigit() else settings.MULTICARD_STORE_ID,
               "amount": o.total * 100, "invoice_id": p.invoice_id, "callback_url": callback_url(), "lang": lang,
               "ttl": settings.MULTICARD_INVOICE_TTL, "ofd": _ofd(o, list(items))}
    if return_url:
        payload["return_url"] = return_url
    if return_error_url:
        payload["return_error_url"] = return_error_url
    if METHODS[method]["type"] == "app":     # to'g'ridan-to'g'ri ilovaga (Payme/Click/Uzum...): Multicard sahifasisiz
        for k in ("lang", "ttl", "return_error_url"):
            payload.pop(k, None)
        payload.update(payment_system=method, billing_id=o.id)
        body = await _call("POST", "/payment", payload)
    else:
        body = await _call("POST", "/payment/invoice", payload)
    d = body.get("data") or {}
    if not d.get("checkout_url"):
        raise PaymentError("Multicard to'lov havolasini bermadi")
    p.provider_uuid, p.checkout_url, p.short_link = d.get("uuid"), d["checkout_url"], d.get("short_link")
    db.add(p)
    await db.flush()
    return p


def payment_dict(p: Payment) -> dict:
    return {"payment_id": p.id, "method": p.method, "status": p.status, "amount": p.amount, "pay_url": p.checkout_url, "short_link": p.short_link,
            "expires_at": p.expires_at.isoformat() if p.expires_at else None,
            "paid_at": p.paid_at.isoformat() if p.paid_at else None, "card": p.card_pan, "receipt_url": p.receipt_url}


async def handle_callback(db, data: dict) -> tuple[bool, str]:
    """Multicard success-callback. (True, ..) = qabul qilindi; (False, sabab) = Multicard to'lovni mijozga qaytaradi."""
    inv = str(data.get("invoice_id") or "")
    p = (await db.execute(select(Payment).where(Payment.invoice_id == inv).with_for_update())).scalar_one_or_none()
    if not p:
        return False, "Invoys topilmadi"
    uuid = str(data.get("uuid") or "")
    if p.status == "paid":                                  # takroriy callback
        return (True, "Allaqachon qabul qilingan") if p.provider_uuid == uuid else (False, "Buyurtma allaqachon to'langan")
    try:
        amount = int(float(data.get("amount")))
    except (TypeError, ValueError):
        return False, "Summa noto'g'ri"
    if amount != p.amount * 100:
        log.error("Multicard summa mos kelmadi: %s kutilgan %s keldi %s", inv, p.amount * 100, amount)
        return False, "Summa mos kelmadi"
    o = await db.get(Order, p.order_id)
    if o.status == "cancelled" or p.status != "pending" or o.pay_status != "pending":
        return False, "Buyurtma bekor qilingan yoki to'lov kutilmayapti"
    await _apply_paid(db, p, o, data, uuid)
    return True, "OK"


async def _apply_paid(db, p: Payment, o: Order, data: dict, uuid: str = ""):
    p.status, p.paid_at, p.provider_uuid = "paid", datetime.now(timezone.utc), uuid or p.provider_uuid
    p.billing_id, p.card_pan, p.ps = data.get("billing_id"), data.get("card_pan"), data.get("ps")
    p.receipt_url, p.raw_callback = data.get("receipt_url"), data
    o.pay_method = METHODS.get(p.method, {}).get("label", o.pay_method)   # hisobotlarda haqiqiy usul ko'rinadi
    await osvc.set_payment(db, o, "paid")
    r = await db.get(Restaurant, o.restaurant_id)
    webhooks.queue_payment(db, o, r, "payment.paid", p)


async def sync_payment(db, p: Payment) -> Payment:
    """Callback kelmagan bo'lsa: Multicard dan holatni so'rab (GET /payment/{uuid}) to'langan bo'lsa tasdiqlaydi."""
    if p.status != "pending" or not p.provider_uuid or not configured():
        return p
    d = (await _call("GET", f"/payment/{p.provider_uuid}")).get("data") or {}
    if d.get("status") != "success":
        return p
    amount = d.get("payment_amount") if d.get("payment_amount") is not None else d.get("total_amount")
    if amount is not None and int(float(amount)) != p.amount * 100:
        log.error("Multicard sync: summa mos kelmadi %s", p.invoice_id)
        return p
    o = await db.get(Order, p.order_id)
    if o.status == "cancelled" or o.pay_status != "pending":
        return p
    await _apply_paid(db, p, o, d, p.provider_uuid)
    return p


async def refund_payment(db, p: Payment) -> Payment:
    """To'langan to'lovni mijozga qaytaradi: DELETE /payment/{uuid} (Multicard)."""
    if p.status not in ("paid", "refund_required"):
        raise PaymentError("Faqat to'langan to'lovni qaytarish mumkin", 409)
    if not p.provider_uuid:
        raise PaymentError("Multicard tranzaksiya ID yo'q", 409)
    await _call("DELETE", f"/payment/{p.provider_uuid}")
    p.status = "refunded"
    o = await db.get(Order, p.order_id)
    if o.pay_status == "paid":
        o.pay_status = "refunded"
    await feed(db, f"To'lov qaytarildi: <b>#{o.id}</b> · {p.amount:,} so'm".replace(",", " "), "amber", o.restaurant_id)
    return p


async def on_order_cancelled(db, o: Order):
    """Buyurtma bekor bo'lganda: to'lanmagan havola bekor, to'langani — qaytarish kerak (operator Multicard kabinetidan qaytaradi)."""
    rows = (await db.execute(select(Payment).where(Payment.order_id == o.id, Payment.status.in_(("pending", "paid"))))).scalars().all()
    for p in rows:
        if p.status == "pending":
            p.status = "cancelled"
        else:
            p.status = "refund_required"
            await feed(db, f"Qaytarish kerak: <b>#{o.id}</b> · {p.amount:,} so'm · Multicard".replace(",", " "), "red", o.restaurant_id)
