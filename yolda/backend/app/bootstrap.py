"""Birinchi platform administratorini yaratish (bo'sh bazada): ADMIN_EMAIL va ADMIN_PASSWORD env orqali."""
import asyncio
import os

from sqlalchemy import select

from app.db import SessionLocal
from app.models import User
from app.security import hash_password


async def main():
    email, pw = os.getenv("ADMIN_EMAIL", "").strip().lower(), os.getenv("ADMIN_PASSWORD", "")
    if not email or not pw:
        print("ADMIN_EMAIL/ADMIN_PASSWORD berilmagan — admin yaratilmadi")
        return
    async with SessionLocal() as db:
        if (await db.execute(select(User.id).limit(1))).first():
            return
        db.add(User(email=email, password_hash=hash_password(pw), full_name="Administrator", role="platform_admin"))
        await db.commit()
        print(f"Administrator yaratildi: {email}")


if __name__ == "__main__":
    asyncio.run(main())
