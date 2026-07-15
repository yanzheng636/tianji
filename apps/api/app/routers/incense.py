from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import get_current_user
from app.models import User
from app.schemas import IncenseOut, LightIncenseIn
from app.services import incense, wish

router = APIRouter(prefix="/api/incense", tags=["incense"])


@router.get("/active", response_model=IncenseOut | None)
async def active(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> IncenseOut | None:
    return await incense.get_active(db, user.id)


@router.post("/light", response_model=IncenseOut)
async def light(
    body: LightIncenseIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> IncenseOut:
    wish_id = None
    if body.wish:
        w = await wish.create(db, user.id, body.wish)
        wish_id = w.id
    return await incense.light(db, user.id, body.type, wish_id)
