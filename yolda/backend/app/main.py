import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app import errors
from app.api.admin import router as admin_router
from app.api.bot.routes import router as bot_router
from app.api.courier import router as courier_router
from app.api.integration import router as integration_router
from app.config import settings
from app.db import SessionLocal
from app.models import User
from app.security import decode_token
from app.ws.manager import manager

log = logging.getLogger("yolda")


@asynccontextmanager
async def lifespan(app: FastAPI):
    tasks = []
    if settings.SECRET_KEY == "change-me-in-production":
        log.warning("SECRET_KEY standart qiymatda — ishlab chiqarishda albatta almashtiring!")
    if not settings.BOT_API_KEY:
        log.warning("BOT_API_KEY bo'sh — Telegram bot integratsiyasi (/api/bot) o'chiq")
    if settings.RUN_WORKERS:
        from app.workers.dispatcher import dispatcher_loop, webhook_loop
        tasks += [asyncio.create_task(dispatcher_loop()), asyncio.create_task(webhook_loop())]
        if settings.DEMO_SIMULATION:
            from app.workers.simulator import simulator_loop
            tasks.append(asyncio.create_task(simulator_loop()))
            log.info("Demo simulyator yoqildi")
    yield
    for t in tasks:
        t.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)


app = FastAPI(title="Yo'lda API", version="1.0", lifespan=lifespan,
              description="Yo'lda yetkazib berish platformasi: admin panel, restoran integratsiyasi (/api/v1), kuryer klienti.")
app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()],
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
errors.install(app)
app.include_router(admin_router)
app.include_router(integration_router)
app.include_router(courier_router)
app.include_router(bot_router)


@app.get("/health", tags=["system"])
async def health():
    return {"ok": True, "simulation": settings.DEMO_SIMULATION, "ws_clients": len(manager.conns)}


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket, token: str = ""):
    data = decode_token(token)
    user = None
    if data and data.get("kind") == "user":
        async with SessionLocal() as db:
            user = await db.get(User, int(data["sub"]))
    if not user or not user.is_active:
        await ws.accept()
        await ws.close(code=4401)
        return
    await manager.connect(ws, user.restaurant_id if user.role == "restaurant_staff" else None)
    try:
        while True:
            msg = await ws.receive_text()
            if msg == "ping":
                await ws.send_text('{"type":"pong","data":{}}')
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(ws)
