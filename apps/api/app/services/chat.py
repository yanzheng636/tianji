"""问卦对话：RAG 注入 + LLM 流式 + 落库。山问人设 + 合规边界 + 多会话管理。"""

from __future__ import annotations

import re
from collections.abc import AsyncGenerator

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import CHAT_MAX_LENGTH
from app.knowledge.graph_catalog import CONCEPTS
from app.models import ChatMessage, ChatSession
from app.providers.llm import get_llm
from app.providers.llm.base import LlmMessage
from app.schemas import ChatMessageOut, ChatSessionOut, CitationOut
from app.services import qian as qian_service
from app.services import quota, scripture

DEFAULT_SESSION_TITLE = "新的一问"

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

SYSTEM_PROMPT = """你是「山问」，一位隐居山中、读过许多古籍的问答者。你说现代白话，语气沉静、克制、有分寸——像一个安静而通透的朋友。不喧哗、不卖弄，绝不使用网络流行语、职场黑话或技术比喻（如「beta」「底层架构」「加载」「上线」「内耗」之类）。

说话的分寸：
- 用平实干净的现代中文，留白多于铺陈；宁可少说一句，也不堆砌辞藻。
- 先安顿对方的心绪，再把话说到点上；不夸大、不制造焦虑，也不敷衍。
- 需要给方向时，落在对方此刻能做、能掌控的一小步，语气是建议而非命令；不要用「小行动：」这类公式化格式，把它自然融进话里。
- 这是一场对谈，不是下判词。多数时候，用一个真诚而具体的问题把话头递回给对方——问问他此刻的处境、感受，或他自己怎么看，让对谈能接着走。是出于关心的好奇，不是盘问；一次只问一件事，问得越具体越好，避免「你觉得呢」这种空泛的话。若对方此刻只是需要被听见，就轻轻收住，不必强行发问。

边界：
1. 你提供的是传统文化的观照与自我梳理，不是预测。绝不承诺改命、保过、或断言某事必然发生。
2. 不给医疗、法律、投资的具体决策；遇到这些，把对方引回「自己能掌控的部分」。
3. 每次回答不超过 150 字，通常两三句：先回应，再把一个问题轻轻递回去。
4. 若给了你【古籍原文】，把它的意思自然化入回答，点到为止，不整段复述、不掉书袋。
5. 不索取、不提及对方的手机号等隐私。"""


def detect_topic(text: str) -> str | None:
    for topic, pat in _TOPIC_PATTERNS:
        if pat.search(text):
            return topic
    return None


# 图谱里既有的概念词表，作为「白话->文言」翻译的受控词汇（命中它们检索最准）。
_CONCEPT_VOCAB = "、".join(sorted({c.name for c in CONCEPTS}))

_QUERY_UNDERSTANDING_PROMPT = (
    "你是古籍检索的查询理解助手。用户用现代口语提问，"
    "你要把它转换成用于检索中国古籍的文言检索词。\n"
    "规则：只输出 2-6 个词，用顿号「、」分隔；不写句子、不加解释、不加标点。"
    "优先选用下列既有概念词，也可补充贴切的文言同义词：\n"
    f"{_CONCEPT_VOCAB}\n"
    "示例：\n"
    "最近工作上的选择让我犹豫 → 事业、官禄、谋事、决疑\n"
    "总是焦虑，怎样把心安定下来 → 修身、养气、安命、心神不宁\n"
    "我该如何面对一段关系的变化 → 姻缘、感情、夫妻、聚散"
)

_TERM_SPLIT = re.compile(r"[、,，;；\s]+")


async def _expand_query(text: str) -> str:
    """让模型把白话问题翻成文言检索词，供确定性图谱检索勾连原典。

    仅做「白话->文言」的查询理解，不生成证据；命中的原文仍来自 verified 图谱节点，
    可溯源性不变。任何失败（含 mock provider）都返回空串，检索退回原句、绝不报错。
    """
    llm = get_llm()
    if getattr(llm, "name", "") == "mock":
        return ""  # mock 无真实理解能力，保持检索行为与 CI 一致
    messages: list[LlmMessage] = [
        {"role": "system", "content": _QUERY_UNDERSTANDING_PROMPT},
        {"role": "user", "content": text},
    ]
    try:
        raw = ""
        async for delta in llm.stream(messages, temperature=0.2, max_tokens=64):
            raw += delta
    except Exception:
        return ""
    terms = [t for t in _TERM_SPLIT.split(raw.strip()) if 1 < len(t) <= 8]
    return " ".join(terms[:6])


def _make_title(text: str) -> str:
    """用首条提问前几字作会话标题。"""
    compact = " ".join(text.split())
    if not compact:
        return DEFAULT_SESSION_TITLE
    return compact[:18] + ("…" if len(compact) > 18 else "")


def _rows_to_messages(rows: list[ChatMessage]) -> list[ChatMessageOut]:
    out: list[ChatMessageOut] = []
    for r in rows:
        cit = CitationOut(**r.citation_json) if r.citation_json else None
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


async def list_sessions(db: AsyncSession, user_id: str, limit: int = 50) -> list[ChatSessionOut]:
    rows = (
        await db.scalars(
            select(ChatSession)
            .where(ChatSession.user_id == user_id)
            .order_by(ChatSession.updated_at.desc())
            .limit(limit)
        )
    ).all()
    return [ChatSessionOut(id=s.id, title=s.title, updated_at=s.updated_at) for s in rows]


async def _newest_session(db: AsyncSession, user_id: str) -> ChatSession | None:
    return await db.scalar(
        select(ChatSession)
        .where(ChatSession.user_id == user_id)
        .order_by(ChatSession.updated_at.desc())
        .limit(1)
    )


async def create_session(db: AsyncSession, user_id: str) -> ChatSessionOut:
    """开一条新会话。若最近一条会话本就是空的，直接复用它，避免连点新建堆出空壳。"""
    newest = await _newest_session(db, user_id)
    if newest is not None:
        cnt = await db.scalar(
            select(func.count()).select_from(ChatMessage).where(
                ChatMessage.session_id == newest.id
            )
        )
        if not cnt:
            return ChatSessionOut(id=newest.id, title=newest.title, updated_at=newest.updated_at)
    session = ChatSession(user_id=user_id, title=DEFAULT_SESSION_TITLE)
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return ChatSessionOut(id=session.id, title=session.title, updated_at=session.updated_at)


async def _owned_session(db: AsyncSession, user_id: str, session_id: str) -> ChatSession | None:
    return await db.scalar(
        select(ChatSession).where(
            ChatSession.id == session_id, ChatSession.user_id == user_id
        )
    )


async def _resolve_session(
    db: AsyncSession, user_id: str, session_id: str | None
) -> ChatSession:
    """定位要写入的会话：显式指定优先；否则用最近一条；都没有就新建。"""
    if session_id:
        owned = await _owned_session(db, user_id, session_id)
        if owned is not None:
            return owned
    newest = await _newest_session(db, user_id)
    if newest is not None:
        return newest
    session = ChatSession(user_id=user_id, title=DEFAULT_SESSION_TITLE)
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def session_messages(
    db: AsyncSession, user_id: str, session_id: str, limit: int = 200
) -> list[ChatMessageOut]:
    if await _owned_session(db, user_id, session_id) is None:
        return []
    rows = (
        await db.scalars(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc())
            .limit(limit)
        )
    ).all()
    return _rows_to_messages(list(rows))


async def delete_session(db: AsyncSession, user_id: str, session_id: str) -> bool:
    if await _owned_session(db, user_id, session_id) is None:
        return False
    await db.execute(delete(ChatSession).where(ChatSession.id == session_id))
    await db.commit()
    return True


async def history(db: AsyncSession, user_id: str, limit: int = 30) -> list[ChatMessageOut]:
    """兼容旧接口：返回最近一条会话的消息（供单会话前端使用）。"""
    newest = await _newest_session(db, user_id)
    if newest is None:
        return []
    return await session_messages(db, user_id, newest.id, limit)


async def _recent_context(
    db: AsyncSession, session_id: str, limit: int = 6
) -> list[LlmMessage]:
    rows = (
        await db.scalars(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
        )
    ).all()
    return [{"role": r.role, "content": r.text} for r in reversed(rows)]


async def stream_reply(
    db: AsyncSession,
    user_id: str,
    text: str,
    qian_id: str | None = None,
    session_id: str | None = None,
) -> AsyncGenerator[dict, None]:
    """产出 SSE 事件字典：{type: session|delta|citation|done|error, ...}"""
    text = text.strip()[:CHAT_MAX_LENGTH]

    # 扣额度
    try:
        await quota.consume(db, user_id, "chat")
    except Exception as e:  # QUOTA_EXCEEDED
        yield {"type": "error", "message": getattr(e, "message", "额度已用完")}
        return

    # 定位会话：首条消息时懒创建；标题取首问前几字。前端据此事件认领新会话 id。
    session = await _resolve_session(db, user_id, session_id)
    is_first = session.title == DEFAULT_SESSION_TITLE
    yield {"type": "session", "sessionId": session.id, "title": session.title}

    topic = detect_topic(text)

    # RAG：先让模型把白话问题翻成文言检索词（跨越「口语↔古籍」的用词鸿沟），
    # 再交给确定性图谱检索最相关的一条古籍原文。
    expansion = await _expand_query(text)
    retrieval_query = f"{text} {expansion}".strip() if expansion else text
    citations = scripture.retrieve(retrieval_query, topic=topic, k=1)
    citation = citations[0] if citations else None

    # 组织给 LLM 的上下文
    llm_messages: list[LlmMessage] = [{"role": "system", "content": SYSTEM_PROMPT}]

    # 若带签，把签面加入上下文
    if qian_id:
        q = await qian_service.get_by_draw_id(db, user_id, qian_id)
        if q:
            story = f"（签题：{q.story}）" if q.story else ""
            llm_messages.append(
                {
                    "role": "system",
                    "content": f"【用户刚求得的签】{q.no}·{q.level}{story}：{q.text} 签解：{q.note}",
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

    # 近几轮历史（仅本会话）
    llm_messages.extend(await _recent_context(db, session.id))
    llm_messages.append({"role": "user", "content": text})

    # 先落库用户消息，并刷新会话标题/时间（列表据此排序、显示）
    user_row = ChatMessage(user_id=user_id, session_id=session.id, role="user", text=text)
    db.add(user_row)
    new_title = _make_title(text) if is_first else session.title
    await db.execute(
        update(ChatSession)
        .where(ChatSession.id == session.id)
        .values(title=new_title, updated_at=func.now())
    )
    await db.commit()
    if is_first:
        yield {"type": "session", "sessionId": session.id, "title": new_title}

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
        session_id=session.id,
        role="assistant",
        text=full,
        citation_json=citation.model_dump(by_alias=True) if citation else None,
    )
    db.add(ai_row)
    await db.execute(
        update(ChatSession).where(ChatSession.id == session.id).values(updated_at=func.now())
    )
    await db.commit()
    await db.refresh(ai_row)

    yield {"type": "done", "messageId": ai_row.id, "sessionId": session.id}
