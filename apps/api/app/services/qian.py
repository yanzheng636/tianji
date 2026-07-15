"""摇签：服务端发签（防前端重摇），按殿的主题加权随机，落库。"""

from __future__ import annotations

import secrets

from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import HALLS
from app.data.qians import QIAN_BY_SLUG, QIANS, Qian
from app.models import QianDraw
from app.schemas import QianOut
from app.services import quota


def _weighted_pick(topic: str | None) -> Qian:
    """与主题匹配的签权重更高，但仍保留随机性（天注定的体感）。"""
    weights: list[int] = []
    for q in QIANS:
        w = 3 if topic and q["topic"] == topic else 1
        weights.append(w)
    total = sum(weights)
    # 用 secrets 取加密级随机，杜绝可预测
    r = secrets.randbelow(total)
    upto = 0
    for q, w in zip(QIANS, weights):
        upto += w
        if r < upto:
            return q
    return QIANS[-1]


async def draw(
    db: AsyncSession,
    user_id: str,
    hall: str,
    topic: str | None,
) -> QianOut:
    # 先扣额度（超限直接抛 429，不发签）
    await quota.consume(db, user_id, "qian")

    eff_topic = topic or HALLS.get(hall, {}).get("topic", "general")
    q = _weighted_pick(eff_topic)

    row = QianDraw(user_id=user_id, hall=hall, topic=eff_topic, qian_slug=q["slug"])
    db.add(row)
    await db.commit()
    await db.refresh(row)

    return QianOut(
        id=row.id,
        no=q["no"],
        level=q["level"],
        text=q["text"],
        src=q["src"],
        note=q["note"],
        topic=q["topic"],
        drawn_at=row.created_at,
    )


async def get_by_draw_id(db: AsyncSession, user_id: str, draw_id: str) -> QianOut | None:
    row = await db.get(QianDraw, draw_id)
    if row is None or row.user_id != user_id:
        return None
    q = QIAN_BY_SLUG.get(row.qian_slug)
    if q is None:
        return None
    return QianOut(
        id=row.id,
        no=q["no"],
        level=q["level"],
        text=q["text"],
        src=q["src"],
        note=q["note"],
        topic=q["topic"],
        drawn_at=row.created_at,
    )
