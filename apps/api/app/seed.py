"""数据库 seed：建表（若无）+ 写入藏经阁语料。

用法：python -m app.seed
幂等：已存在的书按 slug 跳过。
"""

from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.core.db import Base, SessionLocal, engine
from app.data.books import BOOKS
from app.knowledge.topics import extract_tags
from app.models import Book, Passage
from app.providers.llm import get_llm


async def _ensure_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def _seed_books() -> None:
    llm = get_llm()
    async with SessionLocal() as db:
        for sort, book in enumerate(BOOKS):
            exists = await db.scalar(select(Book).where(Book.slug == book["slug"]))
            if exists:
                print(f"  跳过已存在：{book['name']}")
                continue
            b = Book(
                slug=book["slug"],
                char=book["char"],
                name=book["name"],
                meta=book["meta"],
                sort=sort,
            )
            db.add(b)
            await db.flush()

            # 若配了 embedding，顺便算好向量存入；否则留 None（检索走关键词）
            texts = [f"{p['text']} {p['plain']}" for p in book["passages"]]
            vectors = None
            try:
                vectors = await llm.embed(texts)
            except Exception:
                vectors = None

            for i, p in enumerate(book["passages"]):
                tags = extract_tags(p["text"] + p["plain"]) or None
                db.add(
                    Passage(
                        book_id=b.id,
                        chapter=p["chapter"],
                        text=p["text"],
                        plain=p["plain"],
                        topic=p["topic"],
                        tags=tags,
                        embedding=(vectors[i] if vectors else None),
                        sort=i,
                    )
                )
            print(f"  写入：{book['name']}（{len(book['passages'])} 段）")
        await db.commit()


async def main() -> None:
    print("→ 建表（若不存在）…")
    await _ensure_tables()
    print("→ 写入藏经阁语料…")
    await _seed_books()
    print("✓ seed 完成")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
