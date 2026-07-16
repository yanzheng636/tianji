"""签谱运行时：从知识图谱构建产物生成关帝灵签一百签。

摇签、解签、藏经阁走同一份 ``knowledge_wiki/graph.json``：签诗、签级、签解
均取自原典 qian 节点，不再维护手写副本——用户抽到的每一签，都能在藏经阁
翻到同一支。slug 沿用 ``gd-签号``（gd-07、gd-100），与历史抽签记录兼容。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

from app.knowledge.runtime import GraphIndex, get_graph_index

_CN_UNITS = "一二三四五六七八九"

# 括号夹注（含结尾未闭合的 OCR 残注），如 "(曩同昔)"、"(左日右"
_PAREN_RE = re.compile(r"[（(][^（）()]*[）)]?")
_CJK_RE = re.compile(r"[\u3400-\u9fff\uf900-\ufaff]")

# 签解栏目的取用优先级：解曰 > 聖意 > 釋義 > 東坡解/碧仙註
_NOTE_SECTIONS = ("explanation", "sacred_meaning", "interpretation", "commentary")


@dataclass(frozen=True)
class QianEntry:
    slug: str
    number: int
    no: str  # 第七签
    level: str  # 大吉 / 上吉 / 中平 / 下下 …
    story: str  # 签题故事，如「呂洞賓煉丹」
    text: str  # 签诗（原典，按七言四句标点）
    note: str  # 签解（原典「解曰」等栏目）
    src: str  # 《關聖帝君靈籤 · 第七籤》
    topics: tuple[str, ...]  # 图谱标注的意图，用于按殿加权
    source_path: str  # knowledge_wiki 内的词条路径，可溯源


def _parse_number(value: str) -> int | None:
    value = value.strip()
    if value.isdigit():
        return int(value)
    if value in {"百", "一百"}:
        return 100
    if "十" in value:
        tens, _, ones = value.partition("十")
        tens_value = 1 if not tens else _CN_UNITS.find(tens) + 1
        if tens_value <= 0:
            return None
        total = tens_value * 10
        if ones:
            ones_value = _CN_UNITS.find(ones) + 1
            if ones_value <= 0:
                return None
            total += ones_value
        return total
    index = _CN_UNITS.find(value)
    return index + 1 if index >= 0 else None


def _cn_number(value: int) -> str:
    if value == 100:
        return "一百"
    tens, ones = divmod(value, 10)
    ones_part = _CN_UNITS[ones - 1] if ones else ""
    if tens == 0:
        return ones_part
    tens_part = "十" if tens == 1 else _CN_UNITS[tens - 1] + "十"
    return tens_part + ones_part


def _cjk_only(value: str) -> str:
    return "".join(_CJK_RE.findall(value))


def _split_poem(raw: str) -> tuple[str, str]:
    """把签诗原文拆成（故事标题, 标点后的七言四句）。

    原文形如「呂洞賓煉丹仙風道骨本天生…」：故事标题连着 28 字诗句，句间
    或以「。」分隔，句后可能跟校勘记（道■識）与括号夹注。拆分失败时不做
    猜测，原样返回全文，故事留空。
    """
    cleaned = _PAREN_RE.sub("", raw).strip()
    lines: list[str] | None = None
    story = ""

    segments = [seg for seg in cleaned.split("。") if seg.strip()]
    if len(segments) >= 4:
        head = _cjk_only(segments[0])
        rest = [_cjk_only(seg) for seg in segments[1:4]]
        if len(head) >= 7 and all(len(seg) == 7 for seg in rest):
            story, first = head[:-7], head[-7:]
            lines = [first, *rest]
    elif "。" not in cleaned:
        chars = _cjk_only(cleaned)
        if len(chars) >= 28:
            story, poem = chars[:-28], chars[-28:]
            lines = [poem[i : i + 7] for i in range(0, 28, 7)]

    if lines is None:
        return "", cleaned
    return story, f"{lines[0]}，{lines[1]}。{lines[2]}，{lines[3]}。"


def _build_entry(index: GraphIndex, node: dict) -> QianEntry | None:
    metadata = node.get("metadata") if isinstance(node.get("metadata"), dict) else {}
    number = _parse_number(str(metadata.get("number") or ""))
    if number is None:
        return None

    sections: dict[str, list[str]] = {}
    for source_id in node.get("evidence", []):
        source = index.nodes.get(str(source_id))
        if not source:
            continue
        source_meta = source.get("metadata") if isinstance(source.get("metadata"), dict) else {}
        structure = source_meta.get("structure") if isinstance(source_meta.get("structure"), dict) else {}
        section = str(structure.get("section") or "")
        text = str(source_meta.get("text") or "").strip()
        if section and text:
            sections.setdefault(section, []).append(text)

    poem_raw = "".join(sections.get("poem", [])).strip()
    if not poem_raw:
        return None
    story, text = _split_poem(poem_raw)

    note = ""
    for section in _NOTE_SECTIONS:
        texts = sections.get(section)
        if texts:
            note = texts[0].strip()
            break

    cn = _cn_number(number)
    return QianEntry(
        slug=f"gd-{number:02d}",
        number=number,
        no=f"第{cn}签",
        level=str(metadata.get("level") or "").strip() or "中平",
        story=story,
        text=text,
        note=note,
        src=f"《關聖帝君靈籤 · 第{cn}籤》",
        topics=tuple(str(item) for item in node.get("intents", []) if item),
        source_path=str(node.get("path") or ""),
    )


@lru_cache(maxsize=2)
def _build_qianpu(index: GraphIndex) -> tuple[QianEntry, ...]:
    entries: dict[int, QianEntry] = {}
    for node in index.nodes.values():
        if node.get("type") != "qian":
            continue
        entry = _build_entry(index, node)
        if entry is not None:
            entries[entry.number] = entry
    return tuple(entries[number] for number in sorted(entries))


def get_qianpu() -> tuple[QianEntry, ...]:
    """全部签（按签号排序）；图谱缺失时为空元组。"""
    index = get_graph_index()
    if index is None:
        return ()
    return _build_qianpu(index)


def qian_by_slug(slug: str) -> QianEntry | None:
    for entry in get_qianpu():
        if entry.slug == slug:
            return entry
    return None
