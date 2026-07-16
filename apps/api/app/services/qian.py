"""摇签：服务端从原典签谱发签（防前端重摇），按殿的主题加权，落库。

签谱来自 knowledge_wiki 的关帝灵签一百签（app.knowledge.qianpu），与藏经阁、
问卦引用同源；数据库只记录抽签事件。
"""

from __future__ import annotations

import secrets
from collections.abc import AsyncGenerator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import HALLS
from app.core.errors import AppError
from app.knowledge.qianpu import QianEntry, get_qianpu, qian_by_slug
from app.models import QianDraw
from app.providers.llm import get_llm
from app.providers.llm.base import LlmMessage
from app.schemas import QianOut
from app.services import profile, quota

READING_SYSTEM_PROMPT = """你是「山问」的签意解读者。请结合用户命盘（若有）、本次所问主题与签面，
写一段不超过 120 个汉字的观照式解读。严格遵守：不预测吉凶，不承诺结果，不制造恐惧，
不替用户做医疗、法律、投资或重大人生决定。结构固定为：
1. 处境映照：2—3 句，照见用户此刻可能的心绪与拉扯；
2. 今日可做：只给一件当天能完成的具体小事；
3. 收束语：一句克制、安定的话。
直接输出正文，可换行，不使用 Markdown 标题、列表符号或“根据命盘”等生硬措辞。"""

MOCK_READING = (
    "这支签照见的，不是结果已经写定，而是你正站在需要收拢心绪、分清轻重的时刻。"
    "先别急着替未来下结论，留意真正牵动你的那一点。\n"
    "今日可做：写下一个今天能完成的小动作，做完前不再追加答案。\n"
    "心若从容，万事皆缓。"
)


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
        saved=getattr(row, "saved", False),
    )


async def _owned_row(
    db: AsyncSession, user_id: str, draw_id: str
) -> QianDraw | None:
    row = await db.get(QianDraw, draw_id)
    if row is None or row.user_id != user_id:
        return None
    return row


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
    row = await _owned_row(db, user_id, draw_id)
    if row is None:
        return None
    q = qian_by_slug(row.qian_slug)
    if q is None:
        return None
    return _to_out(row, q)


async def set_saved(
    db: AsyncSession, user_id: str, draw_id: str, saved: bool
) -> bool | None:
    """收藏或取消收藏；不存在与越权都返回 None，避免泄露他人记录。"""
    row = await _owned_row(db, user_id, draw_id)
    if row is None:
        return None
    row.saved = saved
    await db.commit()
    return row.saved


async def list_saved(db: AsyncSession, user_id: str) -> list[QianOut]:
    rows = (
        await db.scalars(
            select(QianDraw)
            .where(QianDraw.user_id == user_id, QianDraw.saved.is_(True))
            .order_by(QianDraw.created_at.desc())
        )
    ).all()
    result: list[QianOut] = []
    for row in rows:
        q = qian_by_slug(row.qian_slug)
        if q is not None:
            result.append(_to_out(row, q))
    return result


def _chart_context(chart: object | None) -> str:
    if chart is None:
        return "用户尚未填写生辰，本次只按所问主题与签面观照。"
    day_master = getattr(chart, "day_master", "")
    pillars = "、".join(
        f"{getattr(p, 'gan', '')}{getattr(p, 'zhi', '')}"
        for p in getattr(chart, "pillars", [])
    )
    five_elements = "、".join(
        f"{name}{count}" for name, count in getattr(chart, "five_elements", {}).items()
    )
    summary = getattr(chart, "summary", "")
    return f"四柱：{pillars or '未完整'}；日主：{day_master or '未知'}；五行：{five_elements or '未知'}；简述：{summary}"


async def interpret(
    db: AsyncSession, user_id: str, draw_id: str
) -> AsyncGenerator[dict, None]:
    """流式产出个性化签意事件：delta / done / error。"""
    row = await _owned_row(db, user_id, draw_id)
    if row is None:
        yield {"type": "error", "message": "这支签不存在"}
        return
    q = qian_by_slug(row.qian_slug)
    if q is None:
        yield {"type": "error", "message": "签谱暂时未能展开"}
        return

    try:
        chart = await profile.get_chart(db, user_id)
        llm = get_llm()
        if getattr(llm, "name", "") == "mock":
            yield {"type": "delta", "text": MOCK_READING}
            yield {"type": "done"}
            return

        hall = HALLS.get(row.hall, HALLS["qianfang"])
        messages: list[LlmMessage] = [
            {"role": "system", "content": READING_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"【命盘】{_chart_context(chart)}\n"
                    f"【本次所问】{hall['name']}，主题：{row.topic}\n"
                    f"【签面】{q.no}·{q.level}（签题：{q.story or '无'}）\n"
                    f"签诗：{q.text}\n原典签解：{q.note}"
                ),
            },
        ]
        emitted = False
        generated = ""
        async for delta in llm.stream(messages, temperature=0.65, max_tokens=260):
            if delta:
                emitted = True
                generated += delta
                yield {"type": "delta", "text": delta}
        if not emitted:
            raise RuntimeError("empty reading")
        if "今日可做" not in generated:
            addition = "\n今日可做：把所问之事写成一句话，圈出今天能完成的最小一步。"
            generated += addition
            yield {"type": "delta", "text": addition}
        if generated.count("\n") < 2:
            yield {"type": "delta", "text": "\n心定下来，路会在脚下慢慢清楚。"}
        yield {"type": "done"}
    except Exception:
        yield {"type": "error", "message": "签意暂未展开，请先照见签面"}
