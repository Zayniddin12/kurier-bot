from fastapi import APIRouter

from app.api.admin import analytics, auth, couriers, orders, overview, reports, restaurants

router = APIRouter(prefix="/api/admin")
for m in (auth, overview, orders, couriers, reports, restaurants, analytics):
    router.include_router(m.router)
