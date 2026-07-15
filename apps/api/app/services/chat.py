"""问卦对话：RAG 注入 + LLM 流式 + 落库。天机子人设 + 合规边界。"""

from __future__ import annotations

import re
from collections.abc import AsyncGenerator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import CHAT_MAX_LENGTH
from app.models import ChatMessage
from app.providers.llm import get_llm
from app.providers.llm.base import LlmMessage
from app.schemas import ChatMessageOut, CitationOut
from app.services import qian as qian_service
from app.services import quota, scripture

# 主题识别（决定 RAG 检索方向）
_TOPIC_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("exam", re.compile(r"上岸|考研|考公|考试|升学|面试|复习|学业|学")),
    ("career", re.compile(r"事业|跳槽|晋升|转行|工作|升职|裁员|老板|同事|创业")),
    ("wealth", re.compile(r"财|钱|富|搞钱|收入|投资|生意|副业|买房")),
    ("love", re.compile(r"缘|爱|婚|情|喜欢|脱单|对象|暧昧|异地|分手")),
    ("health", re.compile(r"健康|身体|疾病|生病|康复|寿命|气色|精神|睡眠")),
    ("natal", re.compile(r"本命|命局|八字|日主|格局|面相|手相|骨相|大运|流年")),
    ("divination", re.compile(r"问卦|占卦|起卦|卦象|爻|用神|吉凶|六爻|梅花易数")),
    ("cultivation", re.compile(r"修身|劝善|积德|行善|改过|自省|因果|谦德|立命")),
]

SYSTEM_PROMPT = """你是「天机子」，赛博天机寺的 AI 解签大师。你的语气：懂行、通透、带点互联网黑话的幽默，像一个既读过古籍又混过职场的老友。

严格遵守：
1. 你提供的是【传统文化娱乐与心理疗愈】，不是预测。绝不承诺改命、保过、必然发生某事。
2. 不给医疗、法律、投资的具体决策建议；涉及这些时，引导对方回到「自己能掌控的部分」。
3. 每次回答控制在 120 字以内，先共情、再点破、最后给一个能落地的小行动。
4. 如果给了你【古籍原文】，自然地把它的意思融进回答，但不要生硬复述原文。
5. 不索取、不提及对方的手机号等隐私。"""


def detect_topic(text: str) -> str | None:
    for topic, pat in _TOPIC_PATTERNS:
        if pat.search(text):
            return topic
    return None


async def history(db: AsyncSession, user_id: str, limit: int = 30) -> list[ChatMessageOut]:
    rows = (
        await db.scalars(
            select(ChatMessage)
            .where(ChatMessage.user_id == user_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
        )
    ).all()
    rows = list(reversed(rows))
    out: list[ChatMessageOut] = []
    for r in rows:
        cit = None
        if r.citation_json:
            cit = CitationOut(**r.citation_json)
        out.append(
            ChatMessageOut(
                id=r.id,
                role="user" if r.role == "user" else "assistant",
                text=r.text,
                citation=cit,
                created_at=r.created_at,
            )
        )
    return out


async def _recent_context(db: AsyncSession, user_id: str, limit: int = 6) -> list[LlmMessage]:
    rows = (
        await db.scalars(
            select(ChatMessage)
            .where(ChatMessage.user_id == user_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
        )
    ).all()
    msgs: list[LlmMessage] = []
    for r in reversed(rows):
        msgs.append({"role": r.role, "content": r.text})
    return msgs


async def stream_reply(
    db: AsyncSession,
    user_id: str,
    text: str,
    qian_id: str | None = None,
) -> AsyncGenerator[dict, None]:
    """产出 SSE 事件字典：{type: delta|citation|done|error, ...}"""
    text = text.strip()[:CHAT_MAX_LENGTH]

    # 扣额度
    try:
        await quota.consume(db, user_id, "chat")
    except Exception as e:  # QUOTA_EXCEEDED
        yield {"type": "error", "message": getattr(e, "message", "额度已用完")}
        return

    topic = detect_topic(text)

    # RAG：检索最相关的一条古籍
    citations = await scripture.retrieve(db, text, topic=topic, k=1)
    citation = citations[0] if citations else None

    # 组织给 LLM 的上下文
    llm_messages: list[LlmMessage] = [{"role": "system", "content": SYSTEM_PROMPT}]

    # 若带签，把签面加入上下文
    if qian_id:
        q = await qian_service.get_by_draw_id(db, user_id, qian_id)
        if q:
            llm_messages.append(
                {
                    "role": "system",
                    "content": f"【用户刚求得的签】{q.no}·{q.level}：{q.text} 签解：{q.note}",
                }
            )

    if citation:
        concepts = "、".join(citation.concepts) if citation.concepts else "未标注"
        llm_messages.append(
            {
                "role": "system",
                "content": (
                    f"【可引用的古籍原文】《{citation.book}·{citation.chapter}》：{citation.text}"
                    f"（检索路径：意图={citation.intent or topic}；概念={concepts}；"
                    f"证据质量={citation.quality}）。只能按原文适用条件解释，不得扩写为确定性承诺。"
                ),
            }
        )

    # 近几轮历史
    llm_messages.extend(await _recent_context(db, user_id))
    llm_messages.append({"role": "user", "content": text})

    # 先落库用户消息
    user_row = ChatMessage(user_id=user_id, role="user", text=text)
    db.add(user_row)
    await db.commit()

    # 流式生成
    full = ""
    llm = get_llm()
    try:
        async for delta in llm.stream(llm_messages):
            full += delta
            yield {"type": "delta", "text": delta}
    except Exception as e:  # LLM 故障
        yield {"type": "error", "message": f"天机推演中断：{e}"}
        return

    # citation 事件（放在正文后，前端渲染引用卡片）
    if citation:
        yield {"type": "citation", "citation": citation.model_dump(by_alias=True)}

    # 落库助手消息
    ai_row = ChatMessage(
        user_id=user_id,
        role="assistant",
        text=full,
        citation_json=citation.model_dump(by_alias=True) if citation else None,
    )
    db.add(ai_row)
    await db.commit()
    await db.refresh(ai_row)

    yield {"type": "done", "messageId": ai_row.id}
