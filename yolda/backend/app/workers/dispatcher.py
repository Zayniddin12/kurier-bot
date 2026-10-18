import asyncio
import logging

from app.db import SessionLocal
from app.services import dispatch, webhooks
from app.services.events import commit

log = logging.getLogger("yolda.dispatcher")


async def dispatcher_loop(interval: float = 2.0):
    while True:
        try:
            async with SessionLocal() as db:
                await dispatch.auto_reassign_vehicle(db)
                await dispatch.dispatch_cycle(db)
                await commit(db)
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("dispatcher xatosi")
        await asyncio.sleep(interval)


async def webhook_loop(interval: float = 2.0):
    while True:
        try:
            await webhooks.deliver_pending()
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("webhook xatosi")
        await asyncio.sleep(interval)
