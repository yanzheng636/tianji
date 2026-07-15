"""导出 CowAgent 式结构化 Markdown wiki。

knowledge_wiki/
  index.md            总入口（书目 + 主题索引）
  books/<slug>.md     每本书：章节 → 段落（原文 + 白话 + 标签）
  topics/<topic>.md   按主题聚合的段落索引（便于定位 / 直接取文件式检索）

供人查阅与版本追踪。
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Book, Passage

TOPIC_LABEL = {
    "general": "通用",
    "exam": "升学考试",
    "career": "事业官禄",
    "wealth": "财运财帛",
    "love": "姻缘感情",
    "health": "健康气色",
}


async def export_wiki(session: AsyncSession, out_dir: str = "knowledge_wiki") -> Path:
    root = Path(out_dir)
    (root / "books").mkdir(parents=True, exist_ok=True)
    (root / "topics").mkdir(parents=True, exist_ok=True)

    books = list((await session.scalars(select(Book).order_by(Book.sort, Book.name))).all())
    topic_buckets: dict[str, list[tuple[str, Passage]]] = {}

    for b in books:
        passages = list(
            (
                await session.scalars(
                    select(Passage).where(Passage.book_id == b.id).order_by(Passage.sort)
                )
            ).all()
        )
        lines = [f"# {b.name}", "", f"> {b.meta} · 共 {len(passages)} 段", ""]
        cur_chapter = None
        for p in passages:
            if p.chapter != cur_chapter:
                cur_chapter = p.chapter
                lines += ["", f"## {cur_chapter}", ""]
            tag_str = ("　`" + "` `".join(p.tags) + "`") if p.tags else ""
            lines.append(f"- **原文**：{p.text}{tag_str}")
            if p.plain:
                lines.append(f"  - 白话：{p.plain}")
            topic_buckets.setdefault(p.topic, []).append((b.name, p))
        (root / "books" / f"{b.slug}.md").write_text("\n".join(lines), encoding="utf-8")

    for topic, items in topic_buckets.items():
        label = TOPIC_LABEL.get(topic, topic)
        lines = [f"# 主题索引 · {label}", "", f"> 共 {len(items)} 段", ""]
        for book_name, p in items:
            lines.append(f"- 「{p.text}」——《{book_name} · {p.chapter}》")
        (root / "topics" / f"{topic}.md").write_text("\n".join(lines), encoding="utf-8")

    idx = ["# 藏经阁 · 知识库索引", "", "## 书目", ""]
    for b in books:
        idx.append(f"- [{b.name}](books/{b.slug}.md) — {b.meta}")
    idx += ["", "## 主题索引", ""]
    for topic in sorted(topic_buckets):
        label = TOPIC_LABEL.get(topic, topic)
        idx.append(f"- [{label}](topics/{topic}.md) — {len(topic_buckets[topic])} 段")
    (root / "index.md").write_text("\n".join(idx), encoding="utf-8")

    return root
