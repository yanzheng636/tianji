"""命盘档案：保存出生信息 + 触发八字排盘（带缓存）。"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BirthProfile
from app.schemas import BaziChart, BirthProfileIn
from app.services.bazi import compute_bazi


async def get_profile(db: AsyncSession, user_id: str) -> BirthProfile | None:
    return await db.scalar(select(BirthProfile).where(BirthProfile.user_id == user_id))


async def upsert_profile(
    db: AsyncSession, user_id: str, data: BirthProfileIn
) -> tuple[BirthProfile, BaziChart]:
    chart = compute_bazi(data.birth_date, data.birth_hour, data.gender)

    row = await get_profile(db, user_id)
    if row is None:
        row = BirthProfile(user_id=user_id)
        db.add(row)
    row.gender = data.gender
    row.birth_date = data.birth_date
    row.birth_hour = data.birth_hour
    row.birth_place = data.birth_place
    row.chart_json = chart.model_dump()
    await db.commit()
    await db.refresh(row)
    return row, chart


async def get_chart(db: AsyncSession, user_id: str) -> BaziChart | None:
    row = await get_profile(db, user_id)
    if row is None:
        return None
    if row.chart_json:
        return BaziChart(**row.chart_json)
    chart = compute_bazi(row.birth_date, row.birth_hour, row.gender)
    row.chart_json = chart.model_dump()
    await db.commit()
    return chart
