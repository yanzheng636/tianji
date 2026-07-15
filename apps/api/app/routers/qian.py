from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import get_current_user
from app.models import User
from app.schemas import DrawQianIn, QianOut, QuotaOut
from app.services import qian
from app.services.quota import get_quota

router = APIRouter(prefix="/api/qian", tags=["qian"])


@router.post("/draw", response_model=QianOut)
async def draw(
    body: DrawQianIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QianOut:
    return await qian.draw(db, user.id, body.hall, body.topic)


@router.get("/quota", response_model=QuotaOut)
async def quota(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> QuotaOut:
    return await get_quota(db, user.id, "qian")
