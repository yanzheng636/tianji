"""藏经阁浏览层（app.services.wiki）：证据分页、关键词过滤、词条模糊检索。"""

from types import SimpleNamespace

import app.services.wiki as wiki

CONCEPT_ID = "concept:qian:demo"


def _fake_index(evidence_count: int = 25):
    """构造最小图索引：1 个概念 + N 段证据（奇数段 review-needed，文本带可检索关键词）。"""
    nodes = {
        CONCEPT_ID: {
            "id": CONCEPT_ID,
            "type": "concept",
            "name": "签级",
            "domain": "qian",
            "aliases": ["吉凶等第"],
            "intents": [],
            "evidence": [f"source:demo:{i}" for i in range(evidence_count)],
        }
    }
    for i in range(evidence_count):
        nodes[f"source:demo:{i}"] = {
            "id": f"source:demo:{i}",
            "type": "source",
            "status": "verified" if i % 2 == 0 else "review-needed",
            "path": f"sources/demo.md#s{i}",
            "metadata": {
                "book_id": "demo",
                "book_name": "示例签书",
                "chapter": f"第{i}签",
                "text": f"第{i}段原文" + ("　功名遂" if i % 3 == 0 else "　婚姻聯"),
            },
        }
    return SimpleNamespace(nodes=nodes, edges=[], book_names={"demo": "示例签书"})


def test_concept_evidence_pages_are_stable_and_disjoint(monkeypatch):
    monkeypatch.setattr(wiki, "get_graph_index", _fake_index)

    page0 = wiki.concept_evidence(CONCEPT_ID, offset=0, limit=10)
    page1 = wiki.concept_evidence(CONCEPT_ID, offset=10, limit=10)
    page2 = wiki.concept_evidence(CONCEPT_ID, offset=20, limit=10)

    assert page0["total"] == page1["total"] == 25
    assert [len(p["items"]) for p in (page0, page1, page2)] == [10, 10, 5]
    ids = [e["source_id"] for p in (page0, page1, page2) for e in p["items"]]
    assert len(set(ids)) == 25, "翻页不应重复或丢段"
    # verified 全部排在 review-needed 之前，组内保持原始顺序 → 分页稳定
    qualities = [e["quality"] for p in (page0, page1, page2) for e in p["items"]]
    assert qualities == ["verified"] * 13 + ["review-needed"] * 12

    # 词条详情的第一页与分页接口的第一页一致
    detail = wiki.concept_detail(CONCEPT_ID)
    assert detail["evidence"] == page0["items"][: wiki.MAX_EVIDENCE]
    assert detail["evidence_total"] == 25


def test_concept_evidence_query_requires_all_terms(monkeypatch):
    monkeypatch.setattr(wiki, "get_graph_index", _fake_index)

    hit = wiki.concept_evidence(CONCEPT_ID, query="功名")
    assert hit["total"] == 9  # i % 3 == 0 的 9 段
    assert all("功名" in e["text"] for e in hit["items"])

    # 空格分词 AND：章节 + 正文跨字段同时命中
    both = wiki.concept_evidence(CONCEPT_ID, query="第6签 功名")
    assert both["total"] == 1

    assert wiki.concept_evidence(CONCEPT_ID, query="不存在的词")["total"] == 0


def test_concept_evidence_query_unifies_simplified_and_traditional(monkeypatch):
    """语料是繁体（婚姻聯），简体输入也要能命中；反向粘贴繁体同样可用。"""
    monkeypatch.setattr(wiki, "get_graph_index", _fake_index)

    simplified = wiki.concept_evidence(CONCEPT_ID, query="婚姻联")
    traditional = wiki.concept_evidence(CONCEPT_ID, query="婚姻聯")
    assert simplified["total"] == traditional["total"] == 16  # i % 3 != 0 的 16 段
    assert all("婚姻聯" in e["text"] for e in simplified["items"])  # 展示仍是原文


def test_concept_evidence_unknown_concept_returns_none(monkeypatch):
    monkeypatch.setattr(wiki, "get_graph_index", _fake_index)
    assert wiki.concept_evidence("concept:qian:nope") is None


def test_search_matches_partial_and_full_concept_names(monkeypatch):
    monkeypatch.setattr(wiki, "get_graph_index", _fake_index)
    monkeypatch.setattr(wiki, "retrieve_graph", lambda *args, **kwargs: [])

    # 输入是词条名的一部分（模糊）：签 → 签级
    assert [c["name"] for c in wiki.search("签")["concepts"]] == ["签级"]
    # 别名同样参与模糊匹配
    assert [c["name"] for c in wiki.search("吉凶")["concepts"]] == ["签级"]
    # 原有方向仍然成立：问句里包含词条名
    assert [c["name"] for c in wiki.search("签级是什么意思")["concepts"]] == ["签级"]
    # 粘贴繁体也能命中简体词条名
    assert [c["name"] for c in wiki.search("簽級")["concepts"]] == ["签级"]
    assert wiki.search("八字")["concepts"] == []
