from fastapi import APIRouter

from app.api.admin import analytics, auth, couriers, finance, operator, orders, overview, payments, reports, restaurants

router = APIRouter(prefix="/api/admin")
for m in (auth, overview, orders, operator, couriers, reports, restaurants, analytics, finance, payments):
    router.include_router(m.router)
