"""藏经阁「命理百科」浏览层：领域 → 概念词条 → 原文证据。

只读构建产物 ``knowledge_wiki/graph.json``（经 ``runtime.get_graph_index`` 缓存
在内存），不调用 LLM / embedding / 数据库。与问卦检索共用同一张图，因此
"藏经阁翻到的" 与 "大师引用的" 是同一来源，溯源闭环。

浏览层与检索引擎（runtime.py）刻意分开：本模块只读节点/边并组织成可读词条，
不触碰问卦的确定性检索路径。
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from app.knowledge.graph_catalog import (
    CONCEPT_BY_ID,
    DOMAIN_BY_SLUG,
    DOMAINS,
    INTENT_BY_SLUG,
)
from app.knowledge.runtime import GraphIndex, get_graph_index, retrieve_graph

# 每个领域一个单字图标（与旧藏经阁的书脊单字风格一致）。
DOMAIN_CHAR = {
    "qian": "签",
    "bazi": "命",
    "physiognomy": "相",
    "divination": "易",
    "cultivation": "修",
}

# 词条页原文证据默认一页的条数；全部证据经 /concepts/{id}/evidence 按页翻阅，
# 避免把上百段 OCR 原文一次性倒给用户。
MAX_EVIDENCE = 10

# 概念↔概念关系的中文标签（用于词条页「相关概念」的胶囊）。
RELATION_LABEL = {
    "is_a": "属于",
    "part_of": "组成",
    "depends_on": "依赖",
    "generates": "生",
    "restrains": "克",
    "used_by": "用于",
    "contrasts_with": "相对",
    "differs_from": "区别于",
    "contradicts": "相斥",
}


def _intent_labels(slugs: list[Any]) -> list[str]:
    out: list[str] = []
    for slug in slugs:
        spec = INTENT_BY_SLUG.get(str(slug))
        if spec and spec.name not in out:
            out.append(spec.name)
    return out


def _concept_definition(node: dict[str, Any]) -> str:
    text = str(node.get("description") or "").strip()
    if text:
        return text
    spec = CONCEPT_BY_ID.get(str(node.get("id")))
    return spec.definition if spec else ""


def _book_ref(node: dict[str, Any]) -> dict[str, Any]:
    node_id = str(node.get("id") or "")
    return {
        "slug": node_id.removeprefix("book:"),
        "name": str(node.get("name") or "古籍"),
        "meta": str(node.get("description") or ""),
    }


def list_domains() -> list[dict[str, Any]]:
    """五大道入口卡片：领域 + 概念数 + 原文段数 + 来源书籍。"""
    index = get_graph_index()
    if index is None:
        return []

    concept_count: Counter[str] = Counter()
    passage_count: Counter[str] = Counter()
    books_by_domain: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for node in index.nodes.values():
        node_type = node.get("type")
        domain = str(node.get("domain") or "")
        if node_type == "concept":
            concept_count[domain] += 1
        elif node_type == "source" and node.get("status") != "unusable":
            passage_count[domain] += 1
        elif node_type == "book":
            books_by_domain[domain].append(_book_ref(node))

    out: list[dict[str, Any]] = []
    for spec in DOMAINS:
        out.append(
            {
                "slug": spec.slug,
                "name": spec.name,
                "char": DOMAIN_CHAR.get(spec.slug, spec.name[:1]),
                "description": spec.description,
                "concept_count": concept_count.get(spec.slug, 0),
                "passage_count": passage_count.get(spec.slug, 0),
                "books": sorted(books_by_domain.get(spec.slug, []), key=lambda b: b["name"]),
            }
        )
    return out


def _evidence_total(index: GraphIndex, domain: str) -> int:
    return sum(
        1
        for node in index.nodes.values()
        if node.get("type") == "source"
        and str(node.get("domain") or "") == domain
        and node.get("status") != "unusable"
    )


def domain_detail(slug: str) -> dict[str, Any] | None:
    """领域页：核心概念词条列表 + 来源书籍。"""
    spec = DOMAIN_BY_SLUG.get(slug)
    index = get_graph_index()
    if spec is None or index is None:
        return None

    concepts: list[dict[str, Any]] = []
    books: list[dict[str, Any]] = []
    for node in index.nodes.values():
        if str(node.get("domain") or "") != slug:
            continue
        node_type = node.get("type")
        if node_type == "concept":
            concepts.append(
                {
                    "id": str(node.get("id")),
                    "name": str(node.get("name") or ""),
                    "definition": _concept_definition(node),
                    "intents": _intent_labels(list(node.get("intents", []))),
                    "evidence_count": len(node.get("evidence", []) or []),
                }
            )
        elif node_type == "book":
            books.append(_book_ref(node))

    # 证据多的概念排前面：既是内容最扎实的，也最能立刻展示可溯源。
    concepts.sort(key=lambda c: (-c["evidence_count"], c["name"]))
    books.sort(key=lambda b: b["name"])
    return {
        "slug": spec.slug,
        "name": spec.name,
        "char": DOMAIN_CHAR.get(spec.slug, spec.name[:1]),
        "description": spec.description,
        "concept_count": len(concepts),
        "passage_count": _evidence_total(index, slug),
        "concepts": concepts,
        "books": books,
    }


def _resolve_evidence(index: GraphIndex, source_id: str) -> dict[str, Any] | None:
    node = index.nodes.get(source_id)
    if not node or node.get("type") != "source":
        return None
    status = str(node.get("status") or "review-needed")
    if status == "unusable":
        return None
    metadata = node.get("metadata") if isinstance(node.get("metadata"), dict) else {}
    text = str(metadata.get("text") or node.get("description") or "").strip()
    if not text:
        return None
    book_id = str(metadata.get("book_id") or "")
    if not book_id and source_id.startswith("source:"):
        book_id = source_id.split(":", 2)[1]
    return {
        "source_id": source_id,
        "book": str(metadata.get("book_name") or index.book_names.get(book_id) or "古籍"),
        "chapter": str(metadata.get("chapter") or "正文"),
        "text": text,
        "quality": status,
        "path": str(node.get("path") or ""),
    }


def _related_concepts(index: GraphIndex, concept_id: str) -> list[dict[str, Any]]:
    seen: set[str] = set()
    related: list[dict[str, Any]] = []
    for edge in index.edges:
        source = str(edge.get("source") or "")
        target = str(edge.get("target") or "")
        if not (source.startswith("concept:") and target.startswith("concept:")):
            continue
        if concept_id not in (source, target) or source == target:
            continue
        other = target if source == concept_id else source
        if other in seen:
            continue
        node = index.nodes.get(other)
        if not node:
            continue
        seen.add(other)
        relation = str(edge.get("relation") or "")
        related.append(
            {
                "id": other,
                "name": str(node.get("name") or other),
                "relation": RELATION_LABEL.get(relation, relation),
            }
        )
    related.sort(key=lambda r: r["name"])
    return related


def _collect_evidence(index: GraphIndex, node: dict[str, Any]) -> list[dict[str, Any]]:
    """概念的全部可用证据。verified 排前面（稳定排序保持图谱原始顺序），分页因此稳定。"""
    evidence_all: list[dict[str, Any]] = []
    for source_id in node.get("evidence", []) or []:
        item = _resolve_evidence(index, str(source_id))
        if item is not None:
            evidence_all.append(item)
    # verified 排前面，让最可靠的证据先出现；待校残本仍保留但降序。
    evidence_all.sort(key=lambda e: 0 if e["quality"] == "verified" else 1)
    return evidence_all


def concept_evidence(
    concept_id: str, *, offset: int = 0, limit: int = MAX_EVIDENCE, query: str = ""
) -> dict[str, Any] | None:
    """词条证据翻页：offset/limit 取任意一页；query 按空格分词，全部命中才保留。

    语料多为繁体 OCR，匹配是朴素子串（书名 / 章节 / 正文任一字段），
    不做简繁转换——输入需与原文用字一致。
    """
    index = get_graph_index()
    if index is None:
        return None
    node = index.nodes.get(concept_id)
    if not node or node.get("type") != "concept":
        return None

    items = _collect_evidence(index, node)
    terms = [t for t in query.split() if t]
    if terms:
        items = [
            e
            for e in items
            if all(t in e["text"] or t in e["book"] or t in e["chapter"] for t in terms)
        ]
    return {
        "items": items[offset : offset + limit],
        "total": len(items),
        "offset": offset,
        "limit": limit,
    }


def concept_detail(concept_id: str) -> dict[str, Any] | None:
    """词条页：白话释义 + 相关概念 + 原文证据（verified 优先，其余标注待校）。"""
    index = get_graph_index()
    if index is None:
        return None
    node = index.nodes.get(concept_id)
    if not node or node.get("type") != "concept":
        return None

    domain = str(node.get("domain") or "")
    domain_spec = DOMAIN_BY_SLUG.get(domain)
    evidence_all = _collect_evidence(index, node)

    return {
        "id": concept_id,
        "name": str(node.get("name") or ""),
        "domain": domain,
        "domain_name": domain_spec.name if domain_spec else domain,
        "definition": _concept_definition(node),
        "aliases": [str(a) for a in node.get("aliases", []) if a],
        "intents": _intent_labels(list(node.get("intents", []))),
        "status": str(node.get("status") or "verified"),
        "evidence": evidence_all[:MAX_EVIDENCE],
        "evidence_total": len(evidence_all),
        "related": _related_concepts(index, concept_id),
    }


def _match_concepts(index: GraphIndex, query: str, limit: int) -> list[dict[str, Any]]:
    hits: list[tuple[float, dict[str, Any]]] = []
    for node in index.nodes.values():
        if node.get("type") != "concept":
            continue
        spec = CONCEPT_BY_ID.get(str(node.get("id")))
        terms = {str(node.get("name") or ""), *(str(a) for a in node.get("aliases", []) if a)}
        if spec:
            terms.update(spec.keywords)
            terms.update(spec.aliases)
        # 双向子串：词条名出现在问句里（「印堂发黑怎么办」→ 印堂），
        # 或输入只是词条名的一部分（「关圣」→ 关圣帝君灵签），都算命中。
        score = 0.0
        for term in terms:
            if not term:
                continue
            if term == query:
                score = max(score, 10.0)
            elif len(term) >= 2 and term in query:
                score = max(score, 6.0 + len(term) * 0.3)
            elif query in term:
                score = max(score, 4.0 + len(query) * 0.3)
        if score <= 0:
            continue
        domain = str(node.get("domain") or "")
        domain_spec = DOMAIN_BY_SLUG.get(domain)
        hits.append(
            (
                score,
                {
                    "id": str(node.get("id")),
                    "name": str(node.get("name") or ""),
                    "domain": domain,
                    "domain_name": domain_spec.name if domain_spec else domain,
                    "definition": _concept_definition(node),
                    "evidence_count": len(node.get("evidence", []) or []),
                },
            )
        )
    hits.sort(key=lambda item: (-item[0], -item[1]["evidence_count"], item[1]["name"]))
    return [item[1] for item in hits[:limit]]


def search(query: str, limit: int = 8) -> dict[str, Any]:
    """藏经阁搜索：概念词条命中（主）+ 原文段落命中（复用问卦同一检索）。"""
    query = query.strip()
    if not query:
        return {"concepts": [], "passages": []}
    index = get_graph_index()
    concepts = _match_concepts(index, query, limit) if index is not None else []
    passages = [
        {
            "book": hit.book,
            "chapter": hit.chapter,
            "text": hit.text,
            "quality": hit.quality,
            "source_id": hit.source_id,
            "path": hit.path,
            "concepts": list(hit.concepts),
        }
        for hit in retrieve_graph(query, topic=None, k=limit)
    ]
    return {"concepts": concepts, "passages": passages}
