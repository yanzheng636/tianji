from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.errors import not_found
from app.core.security import get_current_user
from app.models import User
from app.schemas import BaziChart, BirthProfileIn
from app.services import profile

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get("")
async def get_profile(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> dict:
    row = await profile.get_profile(db, user.id)
    if row is None:
        return {"profile": None, "chart": None}
    chart = await profile.get_chart(db, user.id)
    return {
        "profile": {
            "gender": row.gender,
            "birthDate": row.birth_date,
            "birthHour": row.birth_hour,
            "birthPlace": row.birth_place,
        },
        "chart": chart.model_dump(by_alias=True) if chart else None,
    }


@router.put("")
async def upsert_profile(
    body: BirthProfileIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if body.nickname:
        user.nickname = body.nickname
    row, chart = await profile.upsert_profile(db, user.id, body)
    await db.commit()
    return {
        "profile": {
            "gender": row.gender,
            "birthDate": row.birth_date,
            "birthHour": row.birth_hour,
            "birthPlace": row.birth_place,
        },
        "chart": chart.model_dump(by_alias=True),
    }


@router.get("/bazi", response_model=BaziChart)
async def bazi(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> BaziChart:
    chart = await profile.get_chart(db, user.id)
    if chart is None:
        raise not_found("请先在命盘补全生辰")
    return chart
