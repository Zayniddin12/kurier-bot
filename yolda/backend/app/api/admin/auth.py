from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import ROLE_LABELS, current_user
from app.errors import ApiError
from app.models import User
from app.schemas.admin import LoginIn
from app.security import create_token, verify_password

router = APIRouter(tags=["auth"])


def user_out(u: User) -> dict:
    return {"id": u.id, "email": u.email, "full_name": u.full_name, "role": u.role,
            "role_label": ROLE_LABELS.get(u.role, u.role), "restaurant_id": u.restaurant_id}


@router.post("/auth/login")
async def login(body: LoginIn, db: AsyncSession = Depends(get_db)):
    u = (await db.execute(select(User).where(User.email == body.email.strip().lower()))).scalar_one_or_none()
    if not u or not u.is_active or not verify_password(body.password, u.password_hash):
        raise ApiError(401, "Email yoki parol noto'g'ri", "password")
    return {"access_token": create_token(str(u.id)), "token_type": "bearer", "user": user_out(u)}


@router.get("/auth/me")
async def me(u: User = Depends(current_user)):
    return user_out(u)
