"""APP 知识图谱运行时：不调用 LLM 的检索链测试。"""

from __future__ import annotations

import json

from app.knowledge.runtime import GraphHit, retrieve_graph
from app.services import scripture


def _node(node_id: str, node_type: str, name: str, **extra):
    return {
        "id": node_id,
        "type": node_type,
        "name": name,
        "path": extra.pop("path", ""),
        "domain": extra.pop("domain", "divination"),
        "aliases": extra.pop("aliases", []),
        "intents": extra.pop("intents", []),
        "surfaces": extra.pop("surfaces", []),
        "evidence": extra.pop("evidence", []),
        "description": extra.pop("description", ""),
        "status": extra.pop("status", "verified"),
        "metadata": extra.pop("metadata", {}),
        **extra,
    }


def test_graph_retrieval_follows_intent_concept_and_verified_evidence(tmp_path):
    graph = {
        "schema_version": 2,
        "nodes": [
            _node("book:demo", "book", "示例古籍"),
            _node(
                "concept:divination:useful-god",
                "concept",
                "用神",
                aliases=["主用"],
                intents=["divination"],
                evidence=["source:demo:section-0001:passage-00001"],
                metadata={"keywords": ["用神"]},
            ),
            _node(
                "source:demo:section-0001:passage-00001",
                "source",
                "示例古籍 · 用神篇 · 第 1 段",
                path="sources/passages/demo.md#source-demo-section-0001-passage-00001",
                intents=["divination"],
                metadata={
                    "book_id": "demo",
                    "book_name": "示例古籍",
                    "chapter": "用神篇",
                    "text": "凡占先定用神，再察旺衰。",
                    "concepts": ["concept:divination:useful-god"],
                    "structure": {"number_label": "第一籤", "level": "大吉", "section": "poem"},
                },
            ),
        ],
        "edges": [],
    }
    path = tmp_path / "graph.json"
    path.write_text(json.dumps(graph, ensure_ascii=False), encoding="utf-8")

    hits = retrieve_graph("问卦时怎样取用神？", topic="divination", k=2, path=path)

    assert len(hits) == 1
    assert hits[0].book == "示例古籍"
    assert hits[0].chapter == "用神篇"
    assert hits[0].quality == "verified"
    assert hits[0].concepts == ("用神",)
    assert hits[0].structure == {"number_label": "第一籤", "level": "大吉", "section": "poem"}


def test_graph_retrieval_excludes_review_needed_by_default(tmp_path):
    graph = {
        "schema_version": 2,
        "nodes": [
            _node(
                "source:scan:section-0001:passage-00001",
                "source",
                "扫描本 · 正文",
                domain="physiognomy",
                intents=["natal"],
                status="review-needed",
                metadata={"book_name": "扫描本", "chapter": "正文", "text": "鼻为财帛宫。"},
            )
        ],
        "edges": [],
    }
    path = tmp_path / "graph.json"
    path.write_text(json.dumps(graph, ensure_ascii=False), encoding="utf-8")

    assert retrieve_graph("财帛宫", topic="natal", path=path) == []
    assert retrieve_graph("财帛宫", topic="natal", path=path, allow_review=True)


def test_graph_retrieval_does_not_use_intent_as_a_match(tmp_path):
    graph = {
        "schema_version": 2,
        "nodes": [
            _node(
                "source:demo:section-0001:passage-00001",
                "source",
                "示例古籍 · 官禄篇",
                intents=["career"],
                metadata={"book_name": "示例古籍", "chapter": "官禄篇", "text": "仕途贵在勤谨。"},
            )
        ],
        "edges": [],
    }
    path = tmp_path / "graph.json"
    path.write_text(json.dumps(graph, ensure_ascii=False), encoding="utf-8")

    assert retrieve_graph("完全无关的提问", topic="career", path=path) == []


def test_graph_retrieval_scopes_ambiguous_concept_by_intent(tmp_path):
    divination_source = "source:divination:section-0001:passage-00001"
    bazi_source = "source:bazi:section-0001:passage-00001"
    graph = {
        "schema_version": 2,
        "nodes": [
            _node(
                "concept:divination:useful-god",
                "concept",
                "六爻用神",
                intents=["divination"],
                evidence=[divination_source],
                metadata={"keywords": ["用神"]},
            ),
            _node(
                "concept:bazi:useful-god",
                "concept",
                "八字用神",
                domain="bazi",
                intents=["natal"],
                evidence=[bazi_source],
                metadata={"keywords": ["用神"]},
            ),
            _node(
                divination_source,
                "source",
                "卜书 · 用神篇",
                intents=["divination"],
                status="review-needed",
                metadata={"book_name": "卜书", "chapter": "用神篇", "text": "占卦先取用神。"},
            ),
            _node(
                bazi_source,
                "source",
                "命书 · 用神篇",
                domain="bazi",
                intents=["natal"],
                metadata={"book_name": "命书", "chapter": "用神篇", "text": "命局以用神为要。"},
            ),
        ],
        "edges": [],
    }
    path = tmp_path / "graph.json"
    path.write_text(json.dumps(graph, ensure_ascii=False), encoding="utf-8")

    assert retrieve_graph("问卦如何取用神", topic="divination", path=path) == []
    reviewed = retrieve_graph("问卦如何取用神", topic="divination", path=path, allow_review=True)
    assert [hit.book for hit in reviewed] == ["卜书"]


def test_scripture_serves_citations_from_graph(monkeypatch):
    hit = GraphHit(
        source_id="source:demo:1",
        book="示例古籍",
        chapter="用神篇",
        text="凡占先定用神。",
        quality="verified",
        concepts=("用神",),
        intents=("divination",),
        path="sources/passages/demo.md#source-demo-1",
        score=12.0,
    )
    monkeypatch.setattr(scripture, "retrieve_graph", lambda *args, **kwargs: [hit])

    citations = scripture.retrieve("如何取用神", topic="divination", k=1)

    assert citations[0].source_id == hit.source_id
    assert citations[0].concepts == ["用神"]


def test_scripture_returns_nothing_when_graph_has_no_verified_match(monkeypatch):
    # 数据库语料通道已退役：图谱无可靠命中时必须保持「无引用」，没有降级路径。
    monkeypatch.setattr(scripture, "retrieve_graph", lambda *args, **kwargs: [])

    assert scripture.retrieve("无可靠依据的问题", topic="divination") == []


def test_scripture_books_come_from_graph():
    books = scripture.list_books()
    assert len(books) == 13
    slugs = {book.slug for book in books}
    assert "guandi-lingqian" in slugs
    assert all(book.passage_count > 0 for book in books)

    detail = scripture.get_book("guandi-lingqian")
    assert detail is not None
    assert detail.passages
    assert scripture.get_book("no-such-book") is None
