"""每日额度：摇签、问卦限流。供灯用户额度更高。"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import FREE_QUOTA, LAMP_QUOTA
from app.core.config import settings
from app.core.errors import quota_exceeded
from app.models import DailyQuota, Entitlement
from app.schemas import QuotaOut


def _today() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d")


async def is_lamp_user(db: AsyncSession, user_id: str) -> bool:
    now = datetime.now(UTC)
    row = await db.scalar(
        select(Entitlement.id).where(
            Entitlement.user_id == user_id,
            Entitlement.kind == "lamp",
            (Entitlement.expires_at.is_(None)) | (Entitlement.expires_at > now),
        ).limit(1)
    )
    return row is not None


async def limit_for(db: AsyncSession, user_id: str, kind: str) -> int:
    if kind == "qian":
        return settings.qian_daily_limit
    lamp = await is_lamp_user(db, user_id)
    table = LAMP_QUOTA if lamp else FREE_QUOTA
    return table[kind]


async def get_quota(db: AsyncSession, user_id: str, kind: str) -> QuotaOut:
    limit = await limit_for(db, user_id, kind)
    if kind == "qian" and limit == 0:
        return QuotaOut(kind=kind, used=0, limit=0, remaining=0, unlimited=True)
    used = await db.scalar(
        select(DailyQuota.used).where(
            DailyQuota.user_id == user_id,
            DailyQuota.day == _today(),
            DailyQuota.kind == kind,
        )
    ) or 0
    return QuotaOut(kind=kind, used=used, limit=limit, remaining=max(0, limit - used))


async def consume(db: AsyncSession, user_id: str, kind: str) -> QuotaOut:
    """原子 +1，超限抛 429。用 upsert 避免并发下丢计数。"""
    limit = await limit_for(db, user_id, kind)
    if kind == "qian" and limit == 0:
        return QuotaOut(kind=kind, used=0, limit=0, remaining=0, unlimited=True)
    day = _today()

    stmt = (
        pg_insert(DailyQuota)
        .values(user_id=user_id, day=day, kind=kind, used=1)
        .on_conflict_do_update(
            index_elements=["user_id", "day", "kind"],
            set_={"used": DailyQuota.used + 1},
        )
        .returning(DailyQuota.used)
    )
    used = await db.scalar(stmt)
    used = int(used or 1)

    if used > limit:
        # 回滚这次自增，保持计数准确
        await db.execute(
            pg_insert(DailyQuota)
            .values(user_id=user_id, day=day, kind=kind, used=0)
            .on_conflict_do_update(
                index_elements=["user_id", "day", "kind"],
                set_={"used": DailyQuota.used - 1},
            )
        )
        await db.commit()
        raise quota_exceeded(
            "今日免费额度已用完，供一盏长明灯可解锁更多" if kind == "qian" else "今日问卦额度已用完"
        )

    await db.commit()
    return QuotaOut(kind=kind, used=used, limit=limit, remaining=max(0, limit - used))
