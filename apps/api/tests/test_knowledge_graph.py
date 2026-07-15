"""古籍概念知识图谱：确定性解析与关系校验。"""

from app.knowledge.graph_builder import (
    BuildState,
    _derived_node_id,
    assemble_graph,
    build_passages,
    validate_state,
)
from app.knowledge.source_extractors import (
    BookSpec,
    ExtractionResult,
    Section,
    extract_text,
    normalize_text,
    parse_plain_sections,
)


def test_normalize_and_heading_detection_without_short_sentence_false_positive():
    book = BookSpec("demo", "示例书", "demo.txt", "bazi", "测试", "text")
    raw = "\ufeff《示例书》\r\n\r\n卷一 本原\r\n五行者，金木水火土也。\r\n知命。\r\n\r\n用神篇\r\n凡身旺者，宜取泄耗。"
    sections = parse_plain_sections(normalize_text(raw), book)
    assert [section.title for section in sections] == ["卷一 本原", "用神篇"]
    assert "知命。" in sections[0].lines


def test_build_passages_keeps_sentences_and_attaches_concepts():
    book = BookSpec("demo", "示例书", "demo.txt", "bazi", "测试", "text")
    extraction = ExtractionResult(
        book=book,
        sections=[Section("十神", ["正财为日主所克。偏财亦属财星。凡身旺者，宜任财。"])],
        raw_chars=32,
        normalized_chars=32,
        extraction="text",
    )
    passages = build_passages([extraction])
    assert len(passages) == 1
    assert passages[0].text.endswith("宜任财。")
    assert "concept:bazi:direct-wealth" in passages[0].concepts
    assert "wealth" in passages[0].intents


def test_graph_has_app_intents_and_no_dangling_edges():
    book = BookSpec("demo", "示例书", "demo.txt", "bazi", "测试", "text")
    extraction = ExtractionResult(
        book=book,
        sections=[Section("十神", ["正财为日主所克。凡身旺者，宜任财。"])],
        raw_chars=24,
        normalized_chars=24,
        extraction="text",
    )
    passages = build_passages([extraction])
    nodes, edges = assemble_graph(passages, books=(book,))
    assert "domain:bazi" in nodes
    assert "intent:wealth" in nodes
    assert "concept:bazi:direct-wealth" in nodes
    source_node = nodes[passages[0].id]
    assert source_node.metadata["text"] == passages[0].text
    assert source_node.metadata["chapter"] == "十神"
    assert any(edge.target == "intent:wealth" for edge in edges)
    state = BuildState([extraction], passages, nodes, edges, [])
    # 本测试只装入一本书，因此过滤“全量 13 本”这一项，其余结构校验必须通过。
    structural_errors = [error for error in validate_state(state) if not error.startswith("期望 13 本书")]
    assert structural_errors == []


def test_review_needed_source_does_not_create_verified_concept():
    book = BookSpec("scan", "扫描本", "scan.pdf", "bazi", "测试", "pdf")
    extraction = ExtractionResult(
        book=book,
        sections=[Section("十神", ["正财为日主所克。"], quality="review-needed")],
        raw_chars=9,
        normalized_chars=9,
        extraction="mineru",
    )
    passages = build_passages([extraction])
    nodes, _ = assemble_graph(passages, books=(book,))
    assert nodes["concept:bazi:direct-wealth"].status == "review-needed"


def test_second_wave_divination_concepts_are_split_independently():
    book = BookSpec("yi-demo", "易占示例", "demo.txt", "divination", "测试", "text")
    extraction = ExtractionResult(
        book=book,
        sections=[Section("原忌仇神论", ["用神旬空月破，得原神发动；伏神之上为飞神。"])],
        raw_chars=30,
        normalized_chars=30,
        extraction="text",
    )

    passages = build_passages([extraction])

    assert "concept:divination:void-in-decade" in passages[0].concepts
    assert "concept:divination:month-break" in passages[0].concepts
    assert "concept:divination:flying-spirit" in passages[0].concepts
    assert "concept:divination:hidden-spirit" in passages[0].concepts


def test_text_source_reports_replacement_and_truncated_tail(tmp_path):
    source = tmp_path / "broken.txt"
    source.write_text("卷一\n正文完整。\n凡占卦\ufffd", encoding="utf-8")
    book = BookSpec("broken", "残本", source.name, "divination", "测试", "text")
    result = extract_text(source, book)
    assert any("Unicode 替换字符" in warning for warning in result.warnings)
    assert any("结尾疑似截断" in warning for warning in result.warnings)


def test_derived_rule_and_case_ids_are_evidence_stable():
    book = BookSpec("demo", "示例书", "demo.txt", "bazi", "测试", "text")
    extraction = ExtractionResult(
        book=book,
        sections=[Section("十神", ["凡身旺者，宜任财。一人占命，后果显验。"])],
        raw_chars=24,
        normalized_chars=24,
        extraction="text",
    )
    passage = build_passages([extraction])[0]
    rule_id = _derived_node_id("rule", passage, "身旺|宜任财")
    assert rule_id == _derived_node_id("rule", passage, "身旺|宜任财")
    assert rule_id.startswith("rule:demo:")
    assert _derived_node_id("case", passage) != rule_id
    nodes, _ = assemble_graph([passage], books=(book,))
    rule_nodes = [node for node in nodes.values() if node.type == "rule"]
    case_nodes = [node for node in nodes.values() if node.type == "case"]
    assert len(rule_nodes) == 1 and len(case_nodes) == 1
    assert rule_nodes[0].id.rsplit(":", 1)[-1] != "0001"


def test_qian_passage_exposes_source_labelled_structure():
    book = BookSpec("qian-demo", "灵签示例", "demo.epub", "qian", "签谱", "epub")
    extraction = ExtractionResult(
        book=book,
        sections=[Section("第一籤　甲甲　大吉 · 解曰", ["此籤谋望通达，婚姻可成。"])],
        raw_chars=20,
        normalized_chars=20,
        extraction="epub",
    )
    passage = build_passages([extraction])[0]
    assert passage.structure == {
        "number": "一",
        "number_label": "第一籤",
        "level": "大吉",
        "section": "explanation",
        "section_label": "解曰",
    }
    nodes, _ = assemble_graph([passage], books=(book,))
    assert nodes[passage.id].metadata["structure"]["section"] == "explanation"

    traditional_variant = ExtractionResult(
        book=book,
        sections=[Section("第11簽 下下", ["签诗正文内容较长。"])],
        raw_chars=8,
        normalized_chars=8,
        extraction="epub",
    )
    assert build_passages([traditional_variant])[0].structure["level"] == "下下"


def test_qian_sign_is_an_evidence_backed_aggregate_node():
    book = BookSpec("qian-demo", "灵签示例", "demo.epub", "qian", "签谱", "epub")
    extraction = ExtractionResult(
        book=book,
        sections=[
            Section("第一籤　甲甲　大吉", ["典故甲。签诗正文。"]),
            Section("第一籤　甲甲　大吉 · 聖意", ["功名遂，求财平。"]),
        ],
        raw_chars=30,
        normalized_chars=30,
        extraction="epub",
    )
    passages = build_passages([extraction])
    nodes, edges = assemble_graph(passages, books=(book,))
    sign = nodes["qian:qian-demo:一"]
    assert sign.type == "qian"
    assert sign.metadata["level"] == "大吉"
    assert set(sign.evidence) == {passage.id for passage in passages}
    assert any(edge.source == sign.id and edge.relation == "contains" for edge in edges)
