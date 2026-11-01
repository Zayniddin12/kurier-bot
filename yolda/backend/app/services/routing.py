"""Yo'l bo'ylab marshrut (OSRM). Server javob bermasa — to'g'ri chiziq va taxminiy masofa (fallback)."""
import logging
import time

import httpx

from app.config import settings
from app.services.geo import ROAD_FACTOR, haversine

log = logging.getLogger("routing")
CACHE_TTL = 30          # sekund: kuryer harakatlanayotganda ham serverni ortiqcha yuklamaslik uchun
CACHE_MAX = 500
_cache: dict[tuple, tuple[float, dict]] = {}
_client: httpx.AsyncClient | None = None


def _key(a, b) -> tuple:
    return (round(a[0], 4), round(a[1], 4), round(b[0], 4), round(b[1], 4))


def _fallback(a, b) -> dict:
    m = haversine(a[0], a[1], b[0], b[1]) * ROAD_FACTOR * 1000
    return {"distance_m": round(m), "geometry": [[a[0], a[1]], [b[0], b[1]]], "approx": True}


async def leg(a: tuple[float, float], b: tuple[float, float]) -> dict:
    """a, b — (lat, lng). Qaytaradi: distance_m, geometry [[lat, lng], ...], approx (taxminiy bo'lsa True)."""
    k = _key(a, b)
    hit = _cache.get(k)
    if hit and time.monotonic() - hit[0] < CACHE_TTL:
        return hit[1]
    res = None
    if settings.OSRM_URL:
        global _client
        if _client is None:
            _client = httpx.AsyncClient(timeout=4.0)
        try:
            r = await _client.get(f"{settings.OSRM_URL.rstrip('/')}/route/v1/driving/{a[1]},{a[0]};{b[1]},{b[0]}",
                                  params={"overview": "full", "geometries": "geojson"})
            r.raise_for_status()
            rt = r.json()["routes"][0]
            res = {"distance_m": round(rt["distance"]),
                   "geometry": [[lat, lng] for lng, lat in rt["geometry"]["coordinates"]], "approx": False}
        except Exception as e:  # tarmoq, 5xx, noto'g'ri javob — fallback
            log.warning("OSRM xato: %s", e)
    res = res or _fallback(a, b)
    if len(_cache) >= CACHE_MAX:
        _cache.clear()
    _cache[k] = (time.monotonic(), res)
    return res
