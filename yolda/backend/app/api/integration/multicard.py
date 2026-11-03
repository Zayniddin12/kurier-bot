import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_db
from app.services import payments as psvc
from app.services.events import commit

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])
log = logging.getLogger("yolda.payments")


def _client_ip(req: Request) -> str:
    xff = req.headers.get("x-forwarded-for")
    return xff.split(",")[0].strip() if xff else (req.client.host if req.client else "")


@router.post("/multicard/callback", include_in_schema=False)
async def multicard_callback(req: Request, db: AsyncSession = Depends(get_db)):
    """Multicard to'lov muvaffaqiyatli o'tgach shu yerga POST qiladi. Javob {"success": true} bo'lmasa — pul mijozga qaytariladi."""
    allowed = [i.strip() for i in settings.MULTICARD_CALLBACK_IPS.split(",") if i.strip()]
    if allowed and _client_ip(req) not in allowed:
        log.warning("Multicard callback: ruxsatsiz IP %s", _client_ip(req))
        return JSONResponse({"success": False, "message": "Forbidden"}, status_code=403)
    try:
        data = await req.json()
    except ValueError:
        return JSONResponse({"success": False, "message": "Bad request"}, status_code=400)
    if not isinstance(data, dict) or not settings.MULTICARD_SECRET or not psvc.verify_sign(data):
        log.warning("Multicard callback: imzo noto'g'ri (%s)", data.get("invoice_id") if isinstance(data, dict) else None)
        return JSONResponse({"success": False, "message": "Invalid signature"}, status_code=403)
    ok, msg = await psvc.handle_callback(db, data)
    if ok:
        await commit(db)
    else:
        await db.rollback()
        log.warning("Multicard callback rad etildi (%s): %s", data.get("invoice_id"), msg)
    return {"success": ok, "message": msg}
