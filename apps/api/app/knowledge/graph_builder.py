"""从古籍来源生成 CowAgent 风格的概念知识图谱。

用法：
    cd apps/api
    python -m app.knowledge.graph_builder \
      --input-dir ../../../docs/wiki \
      --output-dir ../../../knowledge_wiki \
      --mineru-cache ../../../tmp/mineru

生成过程完全确定性，不调用项目配置的 LLM provider。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path

from app.knowledge.graph_catalog import CONCEPTS, DOMAINS, INTENTS, ConceptSpec
from app.knowledge.source_extractors import (
    BOOK_SPECS,
    BookSpec,
    ExtractionResult,
    Section,
    extract_book,
)

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[。！？；!?])")
_RULE_CONDITION_RE = re.compile(r"(?:^|[。；])[^。；]{0,100}(?:凡|若|如|但|逢|见|見|遇|当|當)[^。；]{0,120}")
_RULE_RESULT_RE = re.compile(r"(?:则|則|主|宜|忌|不可|必|乃|为|為)")
_CASE_RE = re.compile(r"(?:占验|占驗|命例|案例|一士|一人|一女|一男|某氏|某人|昔有|曾有)")
_METHOD_RE = re.compile(r"(?:法|诀|訣|起例|定例|取用|起卦|排盘|排盤|推法|占法)$")


@dataclass
class Passage:
    id: str
    book_id: str
    book_name: str
    domain: str
    chapter: str
    section_sequence: int
    sequence: int
    text: str
    page: int | None
    extraction: str
    quality: str
    intents: list[str] = field(default_factory=list)
    concepts: list[str] = field(default_factory=list)
    # Deterministic, source-derived fields (currently used for 灵签 sections).
    # Kept separate from concepts so consumers can render a qian card without
    # guessing structure from free text.
    structure: dict[str, object] = field(default_factory=dict)

    @property
    def anchor(self) -> str:
        return self.id.replace(":", "-")


@dataclass
class KnowledgeNode:
    id: str
    type: str
    name: str
    path: str
    domain: str | None = None
    aliases: list[str] = field(default_factory=list)
    intents: list[str] = field(default_factory=list)
    surfaces: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    description: str = ""
    status: str = "verified"
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class KnowledgeEdge:
    source: str
    relation: str
    target: str
    evidence: tuple[str, ...] = ()
    status: str = "verified"


@dataclass
class BuildState:
    extractions: list[ExtractionResult]
    passages: list[Passage]
    nodes: dict[str, KnowledgeNode]
    edges: set[KnowledgeEdge]
    warnings: list[str]


def _pack_units(units: list[str], target: int = 120, hard_max: int = 220) -> list[str]:
    output: list[str] = []
    buffer = ""
    for unit in units:
        unit = unit.strip()
        if not unit:
            continue
        if not buffer:
            buffer = unit
            continue
        if len(buffer) >= target or len(buffer) + len(unit) > hard_max:
            output.append(buffer)
            buffer = unit
        else:
            buffer += unit
    if buffer:
        output.append(buffer)
    return output


def _section_passages(section: Section, *, target: int = 120, hard_max: int = 220) -> list[str]:
    raw = "\n".join(line.strip() for line in section.lines if line.strip())
    if not raw:
        return []
    sentences = [item for item in _SENTENCE_SPLIT_RE.split(raw.replace("\n", "")) if item.strip()]
    # OCR 或韵文若缺乏句末标点，以完整排版行作为最小单元，仍不在行内截断。
    if len(sentences) <= 1 and len(raw) > hard_max:
        sentences = [line for line in raw.split("\n") if line.strip()]
    return [item for item in _pack_units(sentences, target, hard_max) if len(item.strip()) >= 8]


def _match_concepts(text: str, domain: str) -> list[str]:
    matches: list[str] = []
    for concept in CONCEPTS:
        if concept.domain != domain:
            continue
        if any(keyword and keyword in text for keyword in concept.keywords):
            matches.append(concept.node_id)
    return matches


_QIAN_NUMBER_RE = re.compile(r"第([一二三四五六七八九十百千万零〇廿卅\d]+)[籤簽签]")
_QIAN_LEVEL_RE = re.compile(r"(大吉|上上吉|上上|上吉|上平|中吉|中平|下吉|下平|下下)")


def _qian_structure(chapter: str, text: str) -> dict[str, object]:
    """Extract the stable fields shared by each 灵签 entry.

    EPUB headings carry the sign number/level and a suffix (聖意、解曰、占驗
    ...).  This is deliberately lexical: it records what the source labels,
    without inferring an interpretation or normalising the poem itself.
    """

    number = _QIAN_NUMBER_RE.search(chapter)
    if not number:
        return {}
    suffix = chapter.rsplit("·", 1)[-1].strip() if "·" in chapter else "签诗"
    section_types = {
        "聖意": "sacred_meaning", "圣意": "sacred_meaning",
        "東坡解": "commentary", "东坡解": "commentary",
        "碧仙註": "commentary", "碧仙注": "commentary",
        "解曰": "explanation", "釋義": "interpretation", "释义": "interpretation",
        "占驗": "verification", "占验": "verification",
    }
    return {
        "number": number.group(1),
        "number_label": number.group(0),
        "level": (_QIAN_LEVEL_RE.search(chapter) or _QIAN_LEVEL_RE.search(text)).group(1)
        if (_QIAN_LEVEL_RE.search(chapter) or _QIAN_LEVEL_RE.search(text)) else None,
        "section": section_types.get(suffix, "poem"),
        "section_label": suffix,
    }


def _classify_intents(text: str, domain: str, concept_ids: list[str]) -> list[str]:
    scores: dict[str, int] = {}
    for intent in INTENTS:
        scores[intent.slug] = sum(text.count(keyword) for keyword in intent.keywords)
    concept_map = {item.node_id: item for item in CONCEPTS}
    for concept_id in concept_ids:
        for intent in concept_map[concept_id].intents:
            scores[intent] = scores.get(intent, 0) + 2
    defaults = {
        "qian": "divination",
        "bazi": "natal",
        "physiognomy": "natal",
        "divination": "divination",
        "cultivation": "cultivation",
    }
    selected = [key for key, score in sorted(scores.items(), key=lambda item: (-item[1], item[0])) if score > 0][:4]
    if not selected:
        selected = [defaults.get(domain, "general")]
    return selected


def _surfaces(domain: str | None, intents: list[str]) -> list[str]:
    surfaces = {"library"}
    if domain == "qian":
        surfaces.update({"qian", "chat"})
    elif domain in {"bazi", "physiognomy"}:
        surfaces.update({"tianji", "chat"})
    elif domain == "divination":
        surfaces.add("chat")
    elif domain == "cultivation":
        surfaces.update({"wish", "chat"})
    if "exam" in intents:
        surfaces.add("wenshu")
    if "love" in intents:
        surfaces.add("yuelao")
    if {"wealth", "career"} & set(intents):
        surfaces.add("caishen")
    if "natal" in intents:
        surfaces.add("tianji")
    return sorted(surfaces)


def build_passages(extractions: list[ExtractionResult]) -> list[Passage]:
    passages: list[Passage] = []
    for extraction in extractions:
        sequence = 0
        for section_sequence, section in enumerate(extraction.sections, start=1):
            for text in _section_passages(section):
                sequence += 1
                searchable = f"{section.title}\n{text}"
                concept_ids = _match_concepts(searchable, extraction.book.domain)
                intents = _classify_intents(searchable, extraction.book.domain, concept_ids)
                passages.append(
                    Passage(
                        id=f"source:{extraction.book.slug}:section-{section_sequence:04d}:passage-{sequence:05d}",
                        book_id=extraction.book.slug,
                        book_name=extraction.book.name,
                        domain=extraction.book.domain,
                        chapter=section.title,
                        section_sequence=section_sequence,
                        sequence=sequence,
                        text=text,
                        page=section.page,
                        extraction=extraction.extraction,
                        quality=section.quality,
                        intents=intents,
                        concepts=concept_ids,
                        structure=_qian_structure(section.title, text)
                        if extraction.book.domain == "qian" else {},
                    )
                )
    return passages


def _add_edge(
    edges: set[KnowledgeEdge],
    source: str,
    relation: str,
    target: str,
    evidence: list[str] | None = None,
    *,
    status: str = "verified",
) -> None:
    edges.add(KnowledgeEdge(source, relation, target, tuple(sorted(evidence or [])), status))


def _rule_parts(text: str) -> tuple[str, str] | None:
    condition_match = _RULE_CONDITION_RE.search(text)
    if not condition_match or not _RULE_RESULT_RE.search(condition_match.group(0)):
        return None
    fragment = condition_match.group(0).strip("。；")
    result_match = _RULE_RESULT_RE.search(fragment)
    if not result_match:
        return None
    return fragment[: result_match.start()].strip("，,；;"), fragment[result_match.start() :].strip()


def _derived_node_id(kind: str, passage: Passage, extra: str = "") -> str:
    """Return a stable id for a node derived from one source passage.

    Rule/case ids used to be allocated as ``0001``, ``0002`` in encounter
    order.  That made every downstream link change when an earlier OCR page
    was added or removed.  The source passage id is already deterministic for
    a given extraction; hashing it (and the parsed payload for rules) keeps the
    human-readable book prefix while making the derived id independent of the
    global counter.
    """

    payload = f"{kind}|{passage.id}|{extra}".encode()
    digest = hashlib.sha1(payload).hexdigest()[:12]
    return f"{kind}:{passage.book_id}:{digest}"


def _concept_link(current_domain: str, target_id: str) -> str:
    _, domain, slug = target_id.split(":", 2)
    if domain == current_domain:
        return f"{slug}.md"
    return f"../{domain}/{slug}.md"


def _source_link(passage: Passage, from_depth: int = 2) -> str:
    prefix = "../" * from_depth
    return f"{prefix}sources/passages/{passage.book_id}.md#{passage.anchor}"


def _evidence_status(evidence: list[str], nodes: dict[str, KnowledgeNode]) -> str:
    statuses = {nodes[source_id].status for source_id in evidence}
    if "verified" in statuses:
        return "verified"
    if "review-needed" in statuses:
        return "review-needed"
    return "unusable"


def assemble_graph(passages: list[Passage], books: tuple[BookSpec, ...] = BOOK_SPECS) -> tuple[dict[str, KnowledgeNode], set[KnowledgeEdge]]:
    nodes: dict[str, KnowledgeNode] = {}
    edges: set[KnowledgeEdge] = set()
    evidence_by_concept: dict[str, list[str]] = defaultdict(list)
    for passage in passages:
        for concept_id in passage.concepts:
            evidence_by_concept[concept_id].append(passage.id)

    for domain in DOMAINS:
        node_id = f"domain:{domain.slug}"
        nodes[node_id] = KnowledgeNode(node_id, "domain", domain.name, f"domains/{domain.slug}.md", domain=domain.slug, description=domain.description)
    for intent in INTENTS:
        node_id = f"intent:{intent.slug}"
        nodes[node_id] = KnowledgeNode(node_id, "intent", intent.name, f"intents/{intent.slug}.md", intents=[intent.slug], description=intent.description)

    for book in books:
        node_id = f"book:{book.slug}"
        nodes[node_id] = KnowledgeNode(node_id, "book", book.name, f"sources/books/{book.slug}.md", domain=book.domain, description=book.meta)
        _add_edge(edges, node_id, "part_of", f"domain:{book.domain}")

    for passage in passages:
        nodes[passage.id] = KnowledgeNode(
            passage.id,
            "source",
            f"{passage.book_name} · {passage.chapter} · 第 {passage.sequence} 段",
            f"sources/passages/{passage.book_id}.md#{passage.anchor}",
            domain=passage.domain,
            intents=passage.intents,
            description=passage.text[:120],
            status=passage.quality,
            metadata={
                "book_id": passage.book_id,
                "book_name": passage.book_name,
                "chapter": passage.chapter,
                "text": passage.text,
                "page": passage.page,
                "sequence": passage.sequence,
                "extraction": passage.extraction,
                "concepts": passage.concepts,
                "structure": passage.structure,
            },
        )
        _add_edge(edges, passage.id, "part_of", f"book:{passage.book_id}")

    # 灵签按“签号”聚合成一等节点；各段仍保留原典证据，避免把圣意/解曰/
    # 占验等不同栏目拼成一段无出处的摘要。
    qian_groups: dict[tuple[str, str], list[Passage]] = defaultdict(list)
    for passage in passages:
        number = passage.structure.get("number") if passage.structure else None
        if number is not None:
            qian_groups[(passage.book_id, str(number))].append(passage)
    qian_nodes: list[KnowledgeNode] = []
    for (book_id, number), items in sorted(qian_groups.items()):
        first = items[0]
        structure = first.structure
        node_id = f"qian:{book_id}:{number}"
        evidence = [item.id for item in items]
        qian_node = KnowledgeNode(
            node_id,
            "qian",
            f"{first.book_name} · {structure.get('number_label', '第' + number + '签')}",
            f"qians/{book_id}-{number}.md",
            domain="qian",
            intents=sorted({intent for item in items for intent in item.intents}),
            surfaces=["qian", "chat", "library"],
            evidence=evidence,
            description=f"签级：{structure.get('level') or '未标注'}；按原典栏目汇总签诗、签解与占验。",
            status=_evidence_status(evidence, nodes),
            metadata={
                "book_id": book_id,
                "number": number,
                "number_label": structure.get("number_label"),
                "level": structure.get("level"),
                "sections": sorted({str(item.structure.get("section")) for item in items}),
            },
        )
        nodes[node_id] = qian_node
        qian_nodes.append(qian_node)
        _add_edge(edges, node_id, "part_of", f"book:{book_id}", evidence)
        for item in items:
            _add_edge(edges, node_id, "contains", item.id, [item.id])

    active_specs: dict[str, ConceptSpec] = {}
    for concept in CONCEPTS:
        evidence = sorted(set(evidence_by_concept.get(concept.node_id, [])))
        if not evidence:
            continue
        active_specs[concept.node_id] = concept
        nodes[concept.node_id] = KnowledgeNode(
            concept.node_id,
            "concept",
            concept.name,
            f"concepts/{concept.domain}/{concept.slug}.md",
            domain=concept.domain,
            aliases=list(concept.aliases),
            intents=list(concept.intents),
            surfaces=_surfaces(concept.domain, list(concept.intents)),
            evidence=evidence,
            description=concept.definition,
            status=_evidence_status(evidence, nodes),
            metadata={
                "keywords": list(concept.keywords),
                "relation_count": len(concept.relations),
            },
        )
        _add_edge(edges, concept.node_id, "part_of", f"domain:{concept.domain}", evidence)
        for intent in concept.intents:
            _add_edge(edges, concept.node_id, "applies_to", f"intent:{intent}", evidence)
        for source_id in evidence:
            _add_edge(edges, source_id, "supports", concept.node_id, [source_id])

    for concept_id, concept in active_specs.items():
        for relation, target_slug in concept.relations:
            target_id = f"concept:{concept.domain}:{target_slug}"
            if target_id not in active_specs:
                # 允许显式跨领域目标，优先按唯一 slug 解析。
                candidates = [item.node_id for item in active_specs.values() if item.slug == target_slug]
                if len(candidates) != 1:
                    continue
                target_id = candidates[0]
            _add_edge(edges, concept_id, relation, target_id, nodes[concept_id].evidence)

    if "concept:qian:qian-level" in active_specs:
        for qian_node in qian_nodes:
            _add_edge(
                edges,
                qian_node.id,
                "has_level",
                "concept:qian:qian-level",
                qian_node.evidence,
            )

    # 原典方法：以明确的方法型章节为单位，不对步骤作无来源补写。
    grouped_sections: dict[tuple[str, int, str], list[Passage]] = defaultdict(list)
    for passage in passages:
        grouped_sections[(passage.book_id, passage.section_sequence, passage.chapter)].append(passage)
    for (book_id, section_sequence, chapter), items in grouped_sections.items():
        if not _METHOD_RE.search(chapter.rstrip("：:")):
            continue
        domain = items[0].domain
        node_id = f"method:{book_id}:section-{section_sequence:04d}"
        evidence = [item.id for item in items]
        intents = sorted({intent for item in items for intent in item.intents})
        nodes[node_id] = KnowledgeNode(
            node_id, "method", chapter, f"methods/{book_id}-section-{section_sequence:04d}.md",
            domain=domain, intents=intents, surfaces=_surfaces(domain, intents), evidence=evidence,
            description=f"《{items[0].book_name}》中“{chapter}”章节整理出的原典方法入口。",
            status=_evidence_status(evidence, nodes),
            metadata={
                "book_id": book_id,
                "inputs": sorted({nodes[source_id].metadata.get("chapter", "") for source_id in evidence})[:8],
                "steps": [item.text for item in items[:8]],
                "output": "依原典步骤形成判断或排演结果",
                "limitations": "仅按原典结构整理；OCR 待复核内容不得作为确定性结论",
                "concepts": sorted({concept for item in items for concept in item.concepts}),
            },
        )
        _add_edge(edges, node_id, "part_of", f"domain:{domain}", evidence)
        for source_id in evidence:
            _add_edge(edges, source_id, "supports", node_id, [source_id])

    # 条件判断规则与案例采用保守模式，每本书限制数量，避免把所有格言机械规则化。
    rule_count: dict[str, int] = defaultdict(int)
    case_count: dict[str, int] = defaultdict(int)
    # Keep the per-book limits, but derive the actual node id from evidence;
    # encounter counters are only used to enforce those limits.
    rule_records: list[tuple[str, Passage, str, str]] = []
    for passage in passages:
        parts = _rule_parts(passage.text)
        if parts and rule_count[passage.book_id] < 30 and passage.quality != "unusable":
            rule_count[passage.book_id] += 1
            condition, conclusion = parts
            node_id = _derived_node_id("rule", passage, f"{condition}|{conclusion}")
            nodes[node_id] = KnowledgeNode(
                node_id, "rule", f"原典规则：{condition[:22]}", f"rules/{passage.book_id}-{node_id.rsplit(':', 1)[-1]}.md",
                domain=passage.domain, intents=passage.intents, surfaces=_surfaces(passage.domain, passage.intents), evidence=[passage.id],
                description=f"条件：{condition}；原文结论：{conclusion}", status=passage.quality,
                metadata={
                    "book_id": passage.book_id,
                    "condition": condition,
                    "conclusion": conclusion,
                    "exceptions": [
                        item.strip()
                        for item in re.split(r"[。；]", passage.text)
                        if re.search(r"(?:但|惟|唯|除|若非|不宜|不可)", item)
                    ][:4],
                    "lineage": passage.book_name,
                    "concepts": passage.concepts,
                },
            )
            rule_records.append((node_id, passage, condition, conclusion))
            _add_edge(edges, passage.id, "supports", node_id, [passage.id])
            _add_edge(edges, node_id, "part_of", f"domain:{passage.domain}", [passage.id])
        if _CASE_RE.search(passage.text) and case_count[passage.book_id] < 20 and passage.quality != "unusable":
            case_count[passage.book_id] += 1
            node_id = _derived_node_id("case", passage)
            nodes[node_id] = KnowledgeNode(
                node_id, "case", f"{passage.book_name}案例 {case_count[passage.book_id]}", f"cases/{passage.book_id}-{node_id.rsplit(':', 1)[-1]}.md",
                domain=passage.domain, intents=passage.intents, surfaces=_surfaces(passage.domain, passage.intents), evidence=[passage.id],
                description=passage.text[:100], status=passage.quality,
            )
            _add_edge(edges, passage.id, "example_of", node_id, [passage.id])

    # 同概念、跨书且结论倾向相反的规则只标为“差异待复核”，不自动裁决为谁对谁错。
    positive = re.compile(r"(?:宜|吉|可|成|利|得|旺)")
    negative = re.compile(r"(?:忌|凶|不可|不宜|难|失|败|克)")
    by_concept: dict[str, list[tuple[str, Passage, str, str]]] = defaultdict(list)
    for record in rule_records:
        for concept_id in record[1].concepts:
            by_concept[concept_id].append(record)
    compared: set[tuple[str, str]] = set()
    for records in by_concept.values():
        for index, left in enumerate(records):
            for right in records[index + 1 :]:
                if left[1].book_id == right[1].book_id:
                    continue
                pair = tuple(sorted((left[0], right[0])))
                if pair in compared:
                    continue
                left_sign = (bool(positive.search(left[3])), bool(negative.search(left[3])))
                right_sign = (bool(positive.search(right[3])), bool(negative.search(right[3])))
                if left_sign not in {(True, False), (False, True)} or right_sign not in {(True, False), (False, True)}:
                    continue
                if left_sign == right_sign:
                    continue
                compared.add(pair)
                evidence = [left[1].id, right[1].id]
                _add_edge(edges, pair[0], "differs_from", pair[1], evidence, status="review-needed")
    return nodes, edges


def _yaml_list(values: list[str]) -> str:
    return "[" + ", ".join(json.dumps(value, ensure_ascii=False) for value in values) + "]"


def _front_matter(node: KnowledgeNode) -> list[str]:
    lines = ["---", f"id: {node.id}", f"type: {node.type}"]
    if node.domain:
        lines.append(f"domain: {node.domain}")
    lines.extend((f"aliases: {_yaml_list(node.aliases)}", f"intents: {_yaml_list(node.intents)}", f"surfaces: {_yaml_list(node.surfaces)}", f"status: {node.status}", "---", ""))
    return lines


def _write(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def write_wiki(output: Path, state: BuildState) -> None:
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    passages_by_id = {passage.id: passage for passage in state.passages}
    domain_names = {domain.slug: domain.name for domain in DOMAINS}
    intent_names = {intent.slug: intent.name for intent in INTENTS}
    outgoing: dict[str, list[KnowledgeEdge]] = defaultdict(list)
    for edge in state.edges:
        outgoing[edge.source].append(edge)

    # 原文证据页与书页
    passages_by_book: dict[str, list[Passage]] = defaultdict(list)
    for passage in state.passages:
        passages_by_book[passage.book_id].append(passage)
    for book in BOOK_SPECS:
        items = passages_by_book.get(book.slug, [])
        book_lines = [f"# {book.name}", "", f"> {book.meta}", "", f"- 知识领域：[{domain_names[book.domain]}](../../domains/{book.domain}.md)", f"- 原文段落：{len(items)}", f"- [查看完整证据段落](../passages/{book.slug}.md)"]
        _write(output / "sources" / "books" / f"{book.slug}.md", book_lines)
        lines = [f"# {book.name} · 原文证据", "", f"> {book.meta} · 共 {len(items)} 段", ""]
        current = None
        for passage in items:
            if passage.chapter != current:
                current = passage.chapter
                lines.extend(("", f"## {current}", ""))
            structure_line = ""
            if passage.structure:
                structure_line = f"- 结构：`{json.dumps(passage.structure, ensure_ascii=False, sort_keys=True)}`"
            lines.extend((f'<a id="{passage.anchor}"></a>', f"### 第 {passage.sequence} 段", "", f"- ID：`{passage.id}`", f"- 页码：{passage.page if passage.page is not None else '—'}", f"- 质量：`{passage.quality}`", f"- 意图：{', '.join(passage.intents)}", f"- 概念：{', '.join(passage.concepts) if passage.concepts else '—'}", structure_line, "", f"> {passage.text}", ""))
        _write(output / "sources" / "passages" / f"{book.slug}.md", lines)

    # 概念页
    concept_specs = {item.node_id: item for item in CONCEPTS}
    for node in [item for item in state.nodes.values() if item.type == "concept"]:
        spec = concept_specs[node.id]
        display_intents = ", ".join(intent_names[item] for item in node.intents) if node.intents else "通用"
        lines = _front_matter(node) + [f"# {node.name}", "", f"> {node.description}", "", "## 核心含义", "", node.description, "", "## 使用范围", "", f"- 知识领域：[{domain_names[spec.domain]}](../../domains/{spec.domain}.md)", f"- APP 意图：{display_intents}", f"- APP 入口：{', '.join(node.surfaces)}", "", "## 相关概念", ""]
        related = [edge for edge in outgoing[node.id] if edge.target.startswith("concept:")]
        if related:
            for edge in sorted(related, key=lambda item: (item.relation, item.target)):
                target = state.nodes[edge.target]
                lines.append(f"- `{edge.relation}` [{target.name}]({_concept_link(spec.domain, target.id)})")
        else:
            lines.append("- 暂无显式关系")
        lines.extend(("", "## 原典依据", ""))
        for source_id in node.evidence[:20]:
            passage = passages_by_id[source_id]
            lines.append(f"- [{passage.book_name} · {passage.chapter} · 第 {passage.sequence} 段]({_source_link(passage)})：{passage.text[:100]}")
        _write(output / node.path, lines)

    # 方法、规则和案例页
    for node in [item for item in state.nodes.values() if item.type in {"method", "rule", "case"}]:
        lines = _front_matter(node) + [f"# {node.name}", "", f"> {node.description}", "", "## 原典依据", ""]
        for source_id in node.evidence:
            passage = passages_by_id[source_id]
            lines.extend((f"- [{passage.book_name} · {passage.chapter} · 第 {passage.sequence} 段]({_source_link(passage, 1)})", f"  - 原文：{passage.text}"))
        if node.type == "method":
            lines.extend(("", "## 输入", ""))
            lines.extend(f"- {item}" for item in node.metadata.get("inputs", []) if item)
            lines.extend(("", "## 步骤", ""))
            lines.extend(
                f"{index}. {item}"
                for index, item in enumerate(node.metadata.get("steps", []), start=1)
            )
            lines.extend(
                (
                    "",
                    "## 输出",
                    "",
                    str(node.metadata.get("output", "—")),
                    "",
                    "## 限制",
                    "",
                    str(node.metadata.get("limitations", "—")),
                )
            )
        if node.type == "rule":
            lines.extend(
                (
                    "",
                    "## 条件",
                    "",
                    str(node.metadata.get("condition", "—")),
                    "",
                    "## 结论",
                    "",
                    str(node.metadata.get("conclusion", "—")),
                    "",
                    "## 例外或限制",
                    "",
                )
            )
            exceptions = node.metadata.get("exceptions", [])
            if isinstance(exceptions, list) and exceptions:
                lines.extend(f"- {item}" for item in exceptions)
            else:
                lines.append("- 原典未在本段明确列出；须结合上下文与相关规则复核。")
            lines.extend(("", "## 使用说明", "", "本页只结构化原典中的条件与结论，不把古籍判断包装为确定性现实承诺。"))
        _write(output / node.path, lines)

    # 灵签聚合页：签号、签级和原典栏目只做结构化展示，不生成现代解读。
    for node in [item for item in state.nodes.values() if item.type == "qian"]:
        lines = _front_matter(node) + [f"# {node.name}", "", f"> {node.description}", ""]
        lines.extend(
            (
                f"- 签号：{node.metadata.get('number_label') or node.metadata.get('number')}",
                f"- 签级：{node.metadata.get('level') or '未标注'}",
                f"- 原典栏目：{', '.join(node.metadata.get('sections', [])) or '—'}",
                "",
                "## 原典分栏",
                "",
            )
        )
        for source_id in node.evidence:
            passage = passages_by_id[source_id]
            section = passage.structure.get("section_label", passage.structure.get("section", ""))
            lines.append(f"- [{section or passage.chapter} · 第 {passage.sequence} 段]({_source_link(passage, 1)})：{passage.text[:120]}")
        _write(output / node.path, lines)

    # 领域与 APP 意图聚合页
    for domain in DOMAINS:
        domain_node = state.nodes[f"domain:{domain.slug}"]
        books = [book for book in BOOK_SPECS if book.domain == domain.slug]
        concepts = sorted((node for node in state.nodes.values() if node.type == "concept" and node.domain == domain.slug), key=lambda item: item.name)
        lines = _front_matter(domain_node) + [f"# {domain.name}", "", f"> {domain.description}", "", "## 来源书籍", ""]
        lines.extend(f"- [{book.name}](../sources/books/{book.slug}.md) — {book.meta}" for book in books)
        lines.extend(("", "## 核心概念", ""))
        lines.extend(f"- [{node.name}](../{node.path}) — {node.description}" for node in concepts)
        _write(output / domain_node.path, lines)

    for intent in INTENTS:
        intent_node = state.nodes[f"intent:{intent.slug}"]
        concepts = sorted((node for node in state.nodes.values() if node.type == "concept" and intent.slug in node.intents), key=lambda item: (item.domain or "", item.name))
        preferred_domains = ", ".join(domain_names[item] for item in intent.preferred_domains)
        lines = _front_matter(intent_node) + [f"# {intent.name}", "", f"> {intent.description}", "", f"优先知识领域：{preferred_domains}", "", "## 相关概念", ""]
        lines.extend(f"- [{node.name}](../{node.path}) — {node.description}" for node in concepts)
        if not concepts:
            lines.append("- 暂无已验证概念")
        _write(output / intent_node.path, lines)

    # 总索引、日志、质量报告和机器可读图
    index = [
        "# 藏经阁 · 概念知识图谱", "", "> 五大知识领域 × APP 用户意图 × 原典证据。", "",
        "> 说明：命理、相法、疾病等内容按历史文献知识保存，不等同于现代医学、法律或确定性现实结论。", "",
        "## 知识领域", "",
    ]
    index.extend(f"- [{domain.name}](domains/{domain.slug}.md) — {domain.description}" for domain in DOMAINS)
    index.extend(("", "## APP 意图", ""))
    index.extend(f"- [{intent.name}](intents/{intent.slug}.md) — {intent.description}" for intent in INTENTS)
    index.extend(("", "## 来源书籍", ""))
    index.extend(f"- [{book.name}](sources/books/{book.slug}.md) — {book.meta}" for book in BOOK_SPECS)
    qian_nodes = sorted((node for node in state.nodes.values() if node.type == "qian"), key=lambda item: item.id)
    if qian_nodes:
        index.extend(("", "## 灵签索引", ""))
        index.extend(f"- [{node.name}]({node.path}) — {node.metadata.get('level') or '未标注'}" for node in qian_nodes)
    _write(output / "index.md", index)
    _write(output / "log.md", ["# Knowledge Log", "", f"## {date.today().isoformat()} ingest | 13 本古籍概念知识图谱", ""])

    tagged_passages = sum(bool(passage.concepts) for passage in state.passages)
    coverage_ratio = tagged_passages / len(state.passages) if state.passages else 0.0
    node_statuses = Counter(node.status for node in state.nodes.values())
    quality = [
        "# 知识库质量报告", "", f"> 生成日期：{date.today().isoformat()}", "",
        "## 总览", "", f"- 书籍：{len(state.extractions)}", f"- 原文段落：{len(state.passages)}",
        f"- 已关联概念的段落：{tagged_passages}（{coverage_ratio:.1%}）",
        f"- 知识节点：{len(state.nodes)}", f"- 关系边：{len(state.edges)}", "",
    ]
    quality.extend(
        (
            "## 节点状态",
            "",
            f"- verified：{node_statuses['verified']}",
            f"- review-needed：{node_statuses['review-needed']}",
            f"- unusable：{node_statuses['unusable']}",
            "",
            "> review-needed / unusable 仅表示来源质量状态；运行时默认不返回 review-needed 证据。",
            "",
        )
    )
    quality.extend(("## 分书统计", ""))
    for extraction in state.extractions:
        items = passages_by_book.get(extraction.book.slug, [])
        ratio = extraction.normalized_chars / extraction.raw_chars if extraction.raw_chars else 0
        quality.extend((f"### {extraction.book.name}", "", f"- 提取方式：`{extraction.extraction}`", f"- 章节：{len(extraction.sections)}", f"- 段落：{len(items)}", f"- 原始字符：{extraction.raw_chars}", f"- 正文字符：{extraction.normalized_chars}", f"- 字符保留比：{ratio:.1%}"))
        if extraction.page_quality:
            page_statuses = Counter(extraction.page_quality.values())
            quality.append(
                "- PDF 页质量："
                f"已验证 {page_statuses['verified']}，待复核 {page_statuses['review-needed']}，"
                f"无可用文本 {page_statuses['unusable']}"
            )
        quality.extend((f"- 警告：{'；'.join(extraction.warnings) if extraction.warnings else '无'}", ""))
        if extraction.page_quality:
            excerpts: dict[int, str] = {}
            for section in extraction.sections:
                if section.page and section.lines and section.page not in excerpts:
                    excerpts[section.page] = "".join(section.lines)[:60]
            queue = [
                f"# {extraction.book.name} · PDF 逐页复核队列",
                "",
                "> 页型由 MinerU 版面块确定；质量升级仍须人工对照原图。",
                "",
                "| 页码 | 页型 | 质量 | OCR 摘要 |",
                "|---:|---|---|---|",
            ]
            for page in sorted(extraction.page_quality):
                excerpt = excerpts.get(page, "—").replace("|", "\\|").replace("\n", " ")
                queue.append(
                    f"| {page} | {extraction.page_kinds.get(page, 'unclassified')} | "
                    f"{extraction.page_quality[page]} | {excerpt} |"
                )
            _write(output / "review-queues" / f"{extraction.book.slug}.md", queue)
    if state.warnings:
        quality.extend(("## 构建警告", ""))
        quality.extend(f"- {warning}" for warning in state.warnings)
    _write(output / "quality-report.md", quality)

    graph = {
        "schema_version": 2,
        "generated_at": date.today().isoformat(),
        "nodes": [asdict(node) for node in sorted(state.nodes.values(), key=lambda item: item.id)],
        "edges": [asdict(edge) | {"evidence": list(edge.evidence)} for edge in sorted(state.edges, key=lambda item: (item.source, item.relation, item.target))],
    }
    (output / "graph.json").write_text(json.dumps(graph, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def validate_state(state: BuildState) -> list[str]:
    errors: list[str] = []
    node_ids = set(state.nodes)
    if len(state.extractions) != len(BOOK_SPECS):
        errors.append(f"期望 {len(BOOK_SPECS)} 本书，实际 {len(state.extractions)} 本")
    for edge in state.edges:
        if edge.source not in node_ids:
            errors.append(f"关系起点不存在：{edge.source}")
        if edge.target not in node_ids:
            errors.append(f"关系终点不存在：{edge.target}")
    for node in state.nodes.values():
        if node.type in {"concept", "method", "rule", "case", "qian"} and not node.evidence:
            errors.append(f"知识节点没有原典证据：{node.id}")
        for evidence in node.evidence:
            if evidence not in node_ids:
                errors.append(f"证据节点不存在：{node.id} -> {evidence}")
    passage_ids = [passage.id for passage in state.passages]
    if len(passage_ids) != len(set(passage_ids)):
        errors.append("原文段落 ID 重复")
    for extraction in state.extractions:
        if not any(passage.book_id == extraction.book.slug for passage in state.passages):
            errors.append(f"书籍没有有效段落：{extraction.book.name}")
    return errors


def validate_output(output: Path) -> list[str]:
    errors: list[str] = []
    anchor_cache: dict[Path, set[str]] = {}
    graph_path = output / "graph.json"
    graph: dict[str, object] = {}
    try:
        graph = json.loads(graph_path.read_text(encoding="utf-8"))
        if not isinstance(graph, dict):
            errors.append("graph.json 根节点必须是对象")
            graph = {}
        elif not isinstance(graph.get("nodes"), list) or not isinstance(graph.get("edges"), list):
            errors.append("graph.json 缺少 nodes 或 edges 数组")
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"graph.json 无法解析：{exc}")
    # 文件链接校验之外，还要验证机器图中的端点、证据 ID 和 path/锚点。
    # 这样 graph.json 被手工编辑或部分复制时，构建会在发布前失败，而不是
    # 运行时返回一个无法打开的引用。
    if isinstance(graph, dict) and isinstance(graph.get("nodes"), list):
        nodes = [node for node in graph["nodes"] if isinstance(node, dict)]
        node_ids = {str(node.get("id")) for node in nodes if node.get("id")}
        for node in nodes:
            node_id = str(node.get("id") or "<unknown>")
            raw_path = str(node.get("path") or "")
            if not raw_path:
                errors.append(f"图谱节点缺少 path：{node_id}")
                continue
            relative_path, _, fragment = raw_path.partition("#")
            resolved = (output / relative_path).resolve()
            try:
                resolved.relative_to(output.resolve())
            except ValueError:
                errors.append(f"图谱节点 path 越出知识库：{node_id} -> {raw_path}")
                continue
            if not resolved.exists():
                errors.append(f"图谱节点 path 不存在：{node_id} -> {raw_path}")
                continue
            if fragment and resolved.suffix == ".md":
                if resolved not in anchor_cache:
                    anchor_cache[resolved] = set(
                        re.findall(r'<a id="([^"]+)"></a>', resolved.read_text(encoding="utf-8"))
                    )
                if fragment not in anchor_cache[resolved]:
                    errors.append(f"图谱节点锚点不存在：{node_id} -> {raw_path}")
            for evidence in node.get("evidence", []) if isinstance(node.get("evidence"), list) else []:
                if str(evidence) not in node_ids:
                    errors.append(f"图谱证据节点不存在：{node_id} -> {evidence}")
        if isinstance(graph.get("edges"), list):
            for edge in graph["edges"]:
                if not isinstance(edge, dict):
                    errors.append("图谱关系不是对象")
                    continue
                source = str(edge.get("source") or "")
                target = str(edge.get("target") or "")
                if source not in node_ids:
                    errors.append(f"图谱关系起点不存在：{source}")
                if target not in node_ids:
                    errors.append(f"图谱关系终点不存在：{target}")
    link_re = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    root = output.resolve()
    for markdown in output.rglob("*.md"):
        text = markdown.read_text(encoding="utf-8")
        for raw_target in link_re.findall(text):
            if raw_target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            target, _, fragment = raw_target.partition("#")
            resolved = (markdown.parent / target).resolve()
            try:
                resolved.relative_to(root)
            except ValueError:
                errors.append(f"链接越出知识库：{markdown.relative_to(output)} -> {raw_target}")
                continue
            if not resolved.exists():
                errors.append(f"链接目标不存在：{markdown.relative_to(output)} -> {raw_target}")
                continue
            if fragment and resolved.suffix == ".md":
                if resolved not in anchor_cache:
                    anchor_cache[resolved] = set(
                        re.findall(r'<a id="([^"]+)"></a>', resolved.read_text(encoding="utf-8"))
                    )
                anchors = anchor_cache[resolved]
                if fragment not in anchors:
                    errors.append(f"链接锚点不存在：{markdown.relative_to(output)} -> {raw_target}")
    return errors


def build(
    input_dir: Path,
    output_dir: Path,
    mineru_cache: Path,
    *,
    mineru_device: str = "cpu",
    mineru_source: str = "modelscope",
) -> BuildState:
    extractions: list[ExtractionResult] = []
    warnings: list[str] = []
    for book in BOOK_SPECS:
        print(f"→ 提取《{book.name}》（{book.source_kind}）")
        extraction = extract_book(book, input_dir, mineru_cache, mineru_device=mineru_device, mineru_source=mineru_source)
        extractions.append(extraction)
        warnings.extend(f"《{book.name}》：{warning}" for warning in extraction.warnings)
    passages = build_passages(extractions)
    nodes, edges = assemble_graph(passages)
    state = BuildState(extractions, passages, nodes, edges, warnings)
    errors = validate_state(state)
    if errors:
        raise RuntimeError("知识图谱校验失败：\n- " + "\n- ".join(errors))
    write_wiki(output_dir, state)
    output_errors = validate_output(output_dir)
    if output_errors:
        raise RuntimeError("知识库文件校验失败：\n- " + "\n- ".join(output_errors))
    print(f"✓ 已生成 {len(passages)} 个段落、{len(nodes)} 个节点、{len(edges)} 条关系")
    return state


def main() -> None:
    parser = argparse.ArgumentParser(description="生成古籍概念知识图谱（不调用 LLM）")
    parser.add_argument("--input-dir", type=Path, default=Path("docs/wiki"))
    parser.add_argument("--output-dir", type=Path, default=Path("knowledge_wiki"))
    parser.add_argument("--mineru-cache", type=Path, default=Path("tmp/mineru"))
    parser.add_argument("--mineru-device", default="cpu")
    parser.add_argument("--mineru-source", default="modelscope", choices=("modelscope", "huggingface", "local"))
    args = parser.parse_args()
    build(args.input_dir.resolve(), args.output_dir.resolve(), args.mineru_cache.resolve(), mineru_device=args.mineru_device, mineru_source=args.mineru_source)


if __name__ == "__main__":
    main()
