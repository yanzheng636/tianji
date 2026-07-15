"""上香：服务端权威计时。改本地时间、换设备都无效——真机也「退出再进还在烧」。"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import INCENSES
from app.core.errors import bad_request
from app.models import IncenseSession
from app.schemas import IncenseOut


def _to_out(row: IncenseSession) -> IncenseOut:
    now = datetime.now(UTC)
    remaining = max(0, int((row.ends_at - now).total_seconds()))
    status = "done" if remaining <= 0 else "burning"
    meta = INCENSES[row.type]
    return IncenseOut(
        id=row.id,
        type=row.type,
        name=meta["name"],
        started_at=row.started_at,
        ends_at=row.ends_at,
        duration_sec=row.duration_sec,
        remaining_sec=remaining,
        status=status,
    )


async def get_active(db: AsyncSession, user_id: str) -> IncenseOut | None:
    """返回用户当前正在燃烧的香（若有）。顺带把已烧完的置为 done。"""
    row = await db.scalar(
        select(IncenseSession)
        .where(IncenseSession.user_id == user_id, IncenseSession.status == "burning")
        .order_by(IncenseSession.started_at.desc())
        .limit(1)
    )
    if row is None:
        return None
    out = _to_out(row)
    if out.status == "done" and row.status == "burning":
        row.status = "done"
        await db.commit()
    return out


async def light(
    db: AsyncSession, user_id: str, incense_type: str, wish_id: str | None = None
) -> IncenseOut:
    # 一次只能烧一炷
    existing = await get_active(db, user_id)
    if existing is not None and existing.status == "burning":
        raise bad_request("已有一炷香在燃烧，香尽方可再上")

    meta = INCENSES[incense_type]
    now = datetime.now(UTC)
    row = IncenseSession(
        user_id=user_id,
        type=incense_type,
        wish_id=wish_id,
        started_at=now,
        ends_at=now + timedelta(seconds=meta["duration_sec"]),
        duration_sec=meta["duration_sec"],
        status="burning",
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return _to_out(row)
