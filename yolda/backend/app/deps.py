from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import Courier, User
from app.security import decode_token

bearer = HTTPBearer(auto_error=False)

ROLE_LABELS = {"platform_admin": "Platforma administratori", "operator": "Smena operatori",
               "restaurant_staff": "Restoran xodimi"}


async def current_user(cred: HTTPAuthorizationCredentials | None = Depends(bearer),
                       db: AsyncSession = Depends(get_db)) -> User:
    if not cred:
        raise HTTPException(401, "Avtorizatsiya talab qilinadi")
    data = decode_token(cred.credentials)
    if not data or data.get("kind") != "user":
        raise HTTPException(401, "Token yaroqsiz yoki muddati tugagan")
    u = await db.get(User, int(data["sub"]))
    if not u or not u.is_active:
        raise HTTPException(401, "Foydalanuvchi topilmadi")
    return u


async def ops_user(u: User = Depends(current_user)) -> User:
    if u.role == "restaurant_staff":
        raise HTTPException(403, "Bu bo'limga ruxsat yo'q")
    return u


def scope_rid(user: User, requested: int | None) -> int | None:
    """Restoran xodimi uchun majburiy filtr."""
    return user.restaurant_id if user.role == "restaurant_staff" else requested


def forced_rid(user: User) -> int | None:
    return user.restaurant_id if user.role == "restaurant_staff" else None


def check_rest_access(user: User, restaurant_id: int):
    if user.role == "restaurant_staff" and user.restaurant_id != restaurant_id:
        raise HTTPException(404, "Topilmadi")


async def current_courier(cred: HTTPAuthorizationCredentials | None = Depends(bearer),
                          db: AsyncSession = Depends(get_db)) -> Courier:
    if not cred:
        raise HTTPException(401, "Avtorizatsiya talab qilinadi")
    data = decode_token(cred.credentials)
    if not data or data.get("kind") != "courier":
        raise HTTPException(401, "Token yaroqsiz")
    c = await db.get(Courier, int(data["sub"]))
    if not c or c.account_status != "active":
        raise HTTPException(401, "Kuryer topilmadi yoki bloklangan")
    return c
