"""许愿池：投币许愿（UGC，过审核）、还愿、公共池漂浮。"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import not_found
from app.models import Wish
from app.providers.moderation import get_moderation
from app.schemas import WishOut, WishPoolOut


def _to_out(row: Wish, mine: bool) -> WishOut:
    return WishOut(
        id=row.id,
        text=row.text,
        status="fulfilled" if row.status == "fulfilled" else "active",
        moderation=row.moderation,  # type: ignore[arg-type]
        moderation_reason=row.moderation_reason,
        created_at=row.created_at,
        fulfilled_at=row.fulfilled_at,
        mine=mine,
    )


async def create(db: AsyncSession, user_id: str, text: str) -> WishOut:
    # UGC 必须过审。审核通过才进公共池；被拒仅本人可见 + 标注原因。
    passed, reason = await get_moderation().check_text(text)
    row = Wish(
        user_id=user_id,
        text=text,
        status="active",
        moderation="approved" if passed else "rejected",
        moderation_reason=reason,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    if not passed:
        # 不抛错——让用户看到自己的愿，但不进公共池；前端可提示未通过
        pass
    return _to_out(row, mine=True)


async def fulfill(db: AsyncSession, user_id: str, wish_id: str) -> WishOut:
    row = await db.get(Wish, wish_id)
    if row is None or row.user_id != user_id:
        raise not_found("愿望不存在")
    if row.status != "fulfilled":
        row.status = "fulfilled"
        row.fulfilled_at = datetime.now(UTC)
        await db.commit()
        await db.refresh(row)
    return _to_out(row, mine=True)


async def pool(db: AsyncSession, user_id: str | None, floating_limit: int = 12) -> WishPoolOut:
    total = await db.scalar(
        select(func.count()).select_from(Wish).where(Wish.moderation == "approved")
    ) or 0

    # 公共池：随机抽一批已通过审核的愿漂浮
    floating_rows = (
        await db.scalars(
            select(Wish)
            .where(Wish.moderation == "approved")
            .order_by(func.random())
            .limit(floating_limit)
        )
    ).all()
    floating = [_to_out(r, mine=bool(user_id) and r.user_id == user_id) for r in floating_rows]

    mine: list[WishOut] = []
    if user_id:
        mine_rows = (
            await db.scalars(
                select(Wish)
                .where(Wish.user_id == user_id)
                .order_by(Wish.created_at.desc())
                .limit(50)
            )
        ).all()
        mine = [_to_out(r, mine=True) for r in mine_rows]

    return WishPoolOut(total=total, floating=floating, mine=mine)
