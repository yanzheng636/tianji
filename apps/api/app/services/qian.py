"""摇签：服务端从原典签谱发签（防前端重摇），按殿的主题加权，落库。

签谱来自 knowledge_wiki 的关帝灵签一百签（app.knowledge.qianpu），与藏经阁、
问卦引用同源；数据库只记录抽签事件。
"""

from __future__ import annotations

import secrets

from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import HALLS
from app.core.errors import AppError
from app.knowledge.qianpu import QianEntry, get_qianpu, qian_by_slug
from app.models import QianDraw
from app.schemas import QianOut
from app.services import quota


def _weighted_pick(topic: str | None) -> QianEntry:
    """与主题匹配的签权重更高，但仍保留随机性（天注定的体感）。"""
    qians = get_qianpu()
    if not qians:
        raise AppError(503, "QIANPU_UNAVAILABLE", "签谱尚未就绪，请稍后再试")
    weights: list[int] = []
    for q in qians:
        w = 3 if topic and topic in q.topics else 1
        weights.append(w)
    total = sum(weights)
    # 用 secrets 取加密级随机，杜绝可预测
    r = secrets.randbelow(total)
    upto = 0
    for q, w in zip(qians, weights):
        upto += w
        if r < upto:
            return q
    return qians[-1]


def _to_out(row: QianDraw, q: QianEntry) -> QianOut:
    return QianOut(
        id=row.id,
        no=q.no,
        level=q.level,
        story=q.story,
        text=q.text,
        src=q.src,
        note=q.note,
        topic=row.topic,
        drawn_at=row.created_at,
    )


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

    row = QianDraw(user_id=user_id, hall=hall, topic=eff_topic, qian_slug=q.slug)
    db.add(row)
    await db.commit()
    await db.refresh(row)

    return _to_out(row, q)


async def get_by_draw_id(db: AsyncSession, user_id: str, draw_id: str) -> QianOut | None:
    row = await db.get(QianDraw, draw_id)
    if row is None or row.user_id != user_id:
        return None
    q = qian_by_slug(row.qian_slug)
    if q is None:
        return None
    return _to_out(row, q)
