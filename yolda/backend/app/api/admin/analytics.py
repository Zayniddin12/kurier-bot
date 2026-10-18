from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import current_user, forced_rid, scope_rid
from app.models import User
from app.services import stats

router = APIRouter(tags=["analytics"])


@router.get("/analytics")
async def analytics(days: int = 7, restaurant_id: int | None = None, u: User = Depends(current_user),
                    db: AsyncSession = Depends(get_db)):
    return await stats.analytics(db, days, scope_rid(u, restaurant_id), forced_rid(u))
