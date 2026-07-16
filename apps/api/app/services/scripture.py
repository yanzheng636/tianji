"""藏经阁 + 可溯源知识检索：全部读取知识图谱构建产物。

书目、原文、引用与命理百科（services.wiki）共用同一份 ``knowledge_wiki/graph.json``，
「藏经阁翻到的」「大师引用的」「摇到的签」三处同源。旧的数据库语料通道已退役：
图谱没有 verified 命中时保持"无引用"，绝不回退到无质量标注的残本。
"""

from __future__ import annotations

from app.knowledge.graph_catalog import DOMAINS
from app.knowledge.runtime import get_graph_index, retrieve_graph
from app.schemas import BookDetailOut, BookSummaryOut, CitationOut, PassageOut
from app.services.wiki import DOMAIN_CHAR

_DOMAIN_ORDER = {spec.slug: index for index, spec in enumerate(DOMAINS)}

# 书页一次返回的原文上限（三命通会有两千余段，全量下发无意义）
MAX_BOOK_PASSAGES = 200


def _book_passages(index, book_id: str) -> list[dict]:
    """书页阅读用原文：保留待复核段（阅读原书 ≠ 引用证据），剔除不可用段。"""
    rows = []
    for node_id, node in index.nodes.items():
        if node.get("type") != "source" or node.get("status") == "unusable":
            continue
        metadata = node.get("metadata") if isinstance(node.get("metadata"), dict) else {}
        if str(metadata.get("book_id") or "") != book_id:
            continue
        rows.append(
            {
                "id": node_id,
                "sequence": int(metadata.get("sequence") or 0),
                "chapter": str(metadata.get("chapter") or "正文"),
                "text": str(metadata.get("text") or node.get("description") or ""),
                "quality": str(node.get("status") or "review-needed"),
            }
        )
    rows.sort(key=lambda item: item["sequence"])
    return rows


def list_books() -> list[BookSummaryOut]:
    index = get_graph_index()
    if index is None:
        return []
    counts: dict[str, int] = {}
    for node in index.nodes.values():
        if node.get("type") != "source" or node.get("status") == "unusable":
            continue
        metadata = node.get("metadata") if isinstance(node.get("metadata"), dict) else {}
        book_id = str(metadata.get("book_id") or "")
        if book_id:
            counts[book_id] = counts.get(book_id, 0) + 1

    books: list[tuple[tuple[int, str], BookSummaryOut]] = []
    for node_id, node in index.nodes.items():
        if node.get("type") != "book":
            continue
        slug = node_id.removeprefix("book:")
        domain = str(node.get("domain") or "")
        books.append(
            (
                (_DOMAIN_ORDER.get(domain, len(_DOMAIN_ORDER)), slug),
                BookSummaryOut(
                    slug=slug,
                    char=DOMAIN_CHAR.get(domain, "典"),
                    name=str(node.get("name") or slug),
                    meta=str(node.get("description") or "古籍"),
                    passage_count=counts.get(slug, 0),
                ),
            )
        )
    return [book for _, book in sorted(books, key=lambda item: item[0])]


def get_book(slug: str) -> BookDetailOut | None:
    index = get_graph_index()
    if index is None:
        return None
    node = index.nodes.get(f"book:{slug}")
    if node is None or node.get("type") != "book":
        return None
    rows = _book_passages(index, slug)
    domain = str(node.get("domain") or "")
    return BookDetailOut(
        slug=slug,
        char=DOMAIN_CHAR.get(domain, "典"),
        name=str(node.get("name") or slug),
        meta=str(node.get("description") or "古籍"),
        passage_count=len(rows),
        passages=[
            PassageOut(
                id=row["id"],
                chapter=row["chapter"],
                text=row["text"],
                plain="",
                quality=row["quality"],
            )
            for row in rows[:MAX_BOOK_PASSAGES]
        ],
    )


def retrieve(query: str, topic: str | None = None, k: int = 1) -> list[CitationOut]:
    """按「意图 -> 概念 -> 一跳关系 -> 原典」检索；只认 verified 证据。"""
    graph_hits = retrieve_graph(query, topic=topic, k=k)
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


def search(q: str, limit: int) -> list[CitationOut]:
    return retrieve(q, topic=None, k=limit)
