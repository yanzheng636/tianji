"""书籍入库 CLI。

用法：
  # 基本（关键词检索，不生成白话）
  python -m app.knowledge.ingest 麻衣相法.txt --slug mayi --name 麻衣相法 --meta "相法 · 三卷 · 宋"

  # 让 LLM 逐段生成白话（需 LLM_PROVIDER=deepseek，mock 下别开）
  python -m app.knowledge.ingest 了凡四训.txt --slug liaofan --name 了凡四训 \
      --meta "劝世 · 明 · 袁黄" --distill

  # 入库后导出 wiki
  python -m app.knowledge.ingest ... --wiki

按 slug 幂等：重复入库会先清掉旧的同名书再写入。
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from sqlalchemy import delete, select

from app.core.db import Base, SessionLocal, engine
from app.knowledge.chunker import Chunk, chunk_text
from app.knowledge.wiki import export_wiki
from app.models import Book, Passage
from app.providers.llm import get_llm


async def _distill_plain(chunks: list[Chunk]) -> None:
    """用 LLM 逐段生成白话（就地写入 chunk.plain）。仅在真实 provider 下有意义。"""
    llm = get_llm()
    for c in chunks:
        prompt = [
            {
                "role": "system",
                "content": "你是古籍白话翻译助手。把用户给的一句文言，用一句不超过40字的现代白话说清楚，只输出白话本身，不要解释。",
            },
            {"role": "user", "content": c.text},
        ]
        buf = ""
        async for delta in llm.stream(prompt, temperature=0.3, max_tokens=120):
            buf += delta
        c.plain = buf.strip()


async def ingest(
    file_path: str,
    slug: str,
    name: str,
    meta: str,
    *,
    default_chapter: str = "正文",
    distill: bool = False,
    make_wiki: bool = False,
) -> int:
    raw = Path(file_path).read_text(encoding="utf-8")
    chunks = chunk_text(raw, default_chapter=default_chapter)
    if not chunks:
        print("⚠️ 没有解析出任何段落，检查文件内容/编码")
        return 0

    print(f"→ 解析出 {len(chunks)} 段")
    if distill:
        print("→ LLM 生成白话中（慢，取决于 provider）…")
        await _distill_plain(chunks)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as db:
        # 幂等：先删旧书（级联删段）
        old = await db.scalar(select(Book).where(Book.slug == slug))
        if old:
            await db.execute(delete(Book).where(Book.id == old.id))
            await db.commit()

        max_sort = await db.scalar(select(Book.sort).order_by(Book.sort.desc()).limit(1)) or 0
        book = Book(slug=slug, char=name[0], name=name, meta=meta, sort=max_sort + 1)
        db.add(book)
        await db.flush()

        for i, c in enumerate(chunks):
            db.add(
                Passage(
                    book_id=book.id,
                    chapter=c.chapter,
                    text=c.text,
                    plain=c.plain,
                    topic=c.topic,
                    tags=c.tags or None,
                    embedding=None,  # 关键词检索；接 pgvector 时在此填向量
                    sort=i,
                )
            )
        await db.commit()
        print(f"✓ 已入库《{name}》：{len(chunks)} 段")

        if make_wiki:
            root = await export_wiki(db)
            print(f"✓ 已导出 wiki 到 {root}/")

    await engine.dispose()
    return len(chunks)


def main() -> None:
    ap = argparse.ArgumentParser(description="古籍入库")
    ap.add_argument("file", help="原文 .txt / .md")
    ap.add_argument("--slug", required=True, help="唯一标识，如 mayi")
    ap.add_argument("--name", required=True, help="书名，如 麻衣相法")
    ap.add_argument("--meta", default="古籍", help='副标题，如 "相法 · 三卷 · 宋"')
    ap.add_argument("--chapter", default="正文", help="无标题时的默认章节名")
    ap.add_argument("--distill", action="store_true", help="用 LLM 逐段生成白话（需真实 provider）")
    ap.add_argument("--wiki", action="store_true", help="入库后导出 knowledge_wiki/")
    args = ap.parse_args()

    asyncio.run(
        ingest(
            args.file,
            slug=args.slug,
            name=args.name,
            meta=args.meta,
            default_chapter=args.chapter,
            distill=args.distill,
            make_wiki=args.wiki,
        )
    )


if __name__ == "__main__":
    main()
