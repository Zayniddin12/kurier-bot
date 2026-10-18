"""Voqealarni yig'ish: tranzaksiya commit bo'lgandan keyin WebSocket orqali yuboriladi."""
import html as _html
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import FeedEvent
from app.ws.manager import manager


def esc(s) -> str:
    return _html.escape(str(s), quote=False)


def emit(db: AsyncSession, type_: str, data: dict, restaurant_id: int | None = None):
    db.info.setdefault("events", []).append((type_, data, restaurant_id))


async def flush_events(db: AsyncSession):
    evs = db.info.pop("events", [])
    for t, d, r in evs:
        await manager.broadcast(t, d, r)
    for fn in db.info.pop("after_commit", []):
        await fn()


async def commit(db: AsyncSession):
    await db.commit()
    await flush_events(db)


async def feed(db: AsyncSession, html_text: str, color: str = "brand", restaurant_id: int | None = None):
    now = datetime.now(timezone.utc)
    ev = FeedEvent(html_text=html_text, color=color, restaurant_id=restaurant_id, created_at=now)
    db.add(ev)
    await db.flush()
    emit(db, "feed", feed_row(ev), restaurant_id)
    return ev


def feed_row(ev: FeedEvent) -> dict:
    return {"id": ev.id, "created_at": ev.created_at.isoformat(), "html": ev.html_text, "color": ev.color,
            "restaurant_id": ev.restaurant_id}
