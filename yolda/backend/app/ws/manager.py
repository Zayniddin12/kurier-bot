import asyncio
import json

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.conns: list[tuple[WebSocket, int | None]] = []

    async def connect(self, ws: WebSocket, restaurant_id: int | None):
        await ws.accept()
        self.conns.append((ws, restaurant_id))

    def disconnect(self, ws: WebSocket):
        self.conns = [c for c in self.conns if c[0] is not ws]

    async def broadcast(self, type_: str, data: dict, restaurant_id: int | None = None):
        """restaurant_id berilsa — faqat shu restoran xodimlari va umumiy (None) foydalanuvchilar oladi."""
        msg = json.dumps({"type": type_, "data": data}, default=str, ensure_ascii=False)
        dead = []
        for ws, rid in list(self.conns):
            if rid is not None and restaurant_id is not None and rid != restaurant_id:
                continue
            if rid is not None and restaurant_id is None and type_ in ("courier.updated",):
                continue
            try:
                await asyncio.wait_for(ws.send_text(msg), timeout=3)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()
