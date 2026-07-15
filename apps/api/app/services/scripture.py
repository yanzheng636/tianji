"""藏经阁 + 可溯源知识检索。

优先走确定性知识图谱；图谱不可用时降级为数据库关键词打分。
检索过程不调用项目 LLM 或 embedding，命中的原文作为 citation 供问卦溯源。
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.knowledge.runtime import get_graph_index, retrieve_graph
from app.models import Book, Passage
from app.schemas import BookDetailOut, BookSummaryOut, CitationOut, PassageOut


async def list_books(db: AsyncSession) -> list[BookSummaryOut]:
    rows = (await db.scalars(select(Book).order_by(Book.sort, Book.name))).all()
    out: list[BookSummaryOut] = []
    for b in rows:
        cnt = await db.scalar(
            select(func.count()).select_from(Passage).where(Passage.book_id == b.id)
        )
        out.append(
            BookSummaryOut(
                slug=b.slug, char=b.char, name=b.name, meta=b.meta, passage_count=cnt or 0
            )
        )
    return out


async def get_book(db: AsyncSession, slug: str) -> BookDetailOut | None:
    b = await db.scalar(select(Book).where(Book.slug == slug))
    if b is None:
        return None
    passages = (
        await db.scalars(
            select(Passage).where(Passage.book_id == b.id).order_by(Passage.sort)
        )
    ).all()
    cnt = len(passages)
    return BookDetailOut(
        slug=b.slug,
        char=b.char,
        name=b.name,
        meta=b.meta,
        passage_count=cnt,
        passages=[
            PassageOut(id=p.id, chapter=p.chapter, text=p.text, plain=p.plain) for p in passages
        ],
    )


def _bigrams(s: str) -> set[str]:
    s = "".join(ch for ch in s if ch.strip())
    return {s[i : i + 2] for i in range(len(s) - 1)} if len(s) >= 2 else set(s)


def _keyword_score(query: str, p: Passage, topic: str | None) -> float:
    """中文关键词打分：主题命中 + 标签命中 + 二元词（bigram）重叠。

    二元词比单字更能反映语义（"文昌"命中比零散的"文""昌"更可信），
    对古籍这种术语固定的语料尤其有效。
    """
    score = 0.0
    if topic and p.topic == topic:
        score += 2.0

    # 标签精确命中（术语级）权重高
    for tag in p.tags or []:
        if tag in query:
            score += 1.2

    # bigram 重叠
    q = _bigrams(query)
    if q:
        doc = _bigrams(p.text) | _bigrams(p.plain)
        overlap = len(q & doc)
        score += overlap * 0.6

    return score


async def retrieve(
    db: AsyncSession, query: str, topic: str | None = None, k: int = 1
) -> list[CitationOut]:
    """按“意图 -> 概念 -> 一跳关系 -> 原典”检索；仅图谱不可用时降级。"""
    graph_available = get_graph_index() is not None
    graph_hits = retrieve_graph(query, topic=topic, k=k)
    if graph_hits:
        return [
            CitationOut(
                book=hit.book,
                chapter=hit.chapter,
                text=hit.text,
                plain=(
                    f"图谱命中：{topic or 'general'}"
                    + (f"；相关概念：{'、'.join(hit.concepts)}" if hit.concepts else "")
                ),
                source_id=hit.source_id,
                quality=hit.quality,
                concepts=list(hit.concepts),
                intent=topic,
                path=hit.path,
                relation_hops=list(hit.relation_hops),
                structure=hit.structure,
            )
            for hit in graph_hits
        ]
    if graph_available:
        # 图谱正常但没有 verified 命中时，必须保持“无引用”；不能回退到
        # 缺少页级质量状态的旧数据库，把待复核残本重新包装成可靠证据。
        return []

    passages = (await db.scalars(select(Passage))).all()
    if not passages:
        return []

    scored = [(_keyword_score(query, passage, topic), passage) for passage in passages]

    scored.sort(key=lambda x: x[0], reverse=True)
    top = [p for s, p in scored[:k] if s > 0]

    result: list[CitationOut] = []
    for p in top:
        book = await db.get(Book, p.book_id)
        result.append(
            CitationOut(
                book=book.name if book else "古籍",
                chapter=p.chapter,
                text=p.text,
                plain=p.plain,
                quality="verified",
                intent=topic,
            )
        )
    return result


async def search(db: AsyncSession, q: str, limit: int) -> list[CitationOut]:
    return await retrieve(db, q, topic=None, k=limit)
