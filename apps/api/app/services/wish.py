"""个人愿池：记录愿望、还愿，并只向本人返回愿望历史。"""

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
    # 审核结果只作为服务端防御信息保留，不影响本人查看自己的愿望。
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
    # 保留 floating_limit 参数，避免破坏现有内部调用；个人愿池不再抽取公共内容。
    _ = floating_limit
    if not user_id:
        return WishPoolOut(total=0, floating=[], mine=[])

    total = await db.scalar(
        select(func.count()).select_from(Wish).where(Wish.user_id == user_id)
    ) or 0
    mine_rows = (
        await db.scalars(
            select(Wish)
            .where(Wish.user_id == user_id)
            .order_by(Wish.created_at.desc())
            .limit(200)
        )
    ).all()
    mine = [_to_out(row, mine=True) for row in mine_rows]
    return WishPoolOut(total=total, floating=[], mine=mine)
