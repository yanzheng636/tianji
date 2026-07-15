"""古籍分章分段器（纯函数，可单测）。

策略：
 1. 先按标题行（卷/篇/章/第…签）切成若干「章节」；
 2. 章节正文按句末标点（。！？；）聚成目标长度的「段」，不破句；
 3. 每段带 chapter / 原文 text / topic / tags。

对文言文调优：句子短、以标点密集，故段目标长度取 60~180 字之间。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.knowledge.topics import classify_topic, extract_tags, looks_like_heading

_SENT_SPLIT = re.compile(r"(?<=[。！？；])")
# markdown 标题
_MD_HEADING = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$")


@dataclass
class Chunk:
    chapter: str
    text: str
    topic: str = "general"
    tags: list[str] = field(default_factory=list)
    plain: str = ""  # 白话，留给 LLM/人工填


def _normalize(raw: str) -> str:
    raw = raw.replace("\r\n", "\n").replace("\r", "\n")
    # 全角空格 → 半角；去零宽字符
    raw = raw.replace("　", " ").replace("﻿", "")
    return raw


def _pack_sentences(sentences: list[str], target: int = 120, hard_max: int = 220) -> list[str]:
    """把句子聚成不破句的段。"""
    out: list[str] = []
    buf = ""
    for s in sentences:
        s = s.strip()
        if not s:
            continue
        if not buf:
            buf = s
        elif len(buf) + len(s) <= hard_max:
            buf += s
            if len(buf) >= target:
                out.append(buf)
                buf = ""
        else:
            out.append(buf)
            buf = s
    if buf:
        out.append(buf)
    return out


def chunk_text(
    raw: str,
    default_chapter: str = "正文",
    target: int = 120,
    hard_max: int = 220,
    min_len: int = 8,
) -> list[Chunk]:
    """把整本原文拆成带章节归属的段落列表。"""
    raw = _normalize(raw)
    lines = raw.split("\n")

    # 收集 (chapter, 正文文本块) 序列
    sections: list[tuple[str, list[str]]] = []
    cur_chapter = default_chapter
    cur_body: list[str] = []

    def flush():
        if cur_body:
            sections.append((cur_chapter, cur_body.copy()))
            cur_body.clear()

    for line in lines:
        stripped = line.strip()
        md = _MD_HEADING.match(line)
        if md:
            flush()
            cur_chapter = md.group(1).strip()
            continue
        if looks_like_heading(stripped):
            flush()
            cur_chapter = stripped.rstrip("：:　 ")
            continue
        if stripped:
            cur_body.append(stripped)
    flush()

    # 每个 section 内聚段
    chunks: list[Chunk] = []
    for chapter, body in sections:
        joined = "".join(body)
        sentences = _SENT_SPLIT.split(joined)
        for para in _pack_sentences(sentences, target, hard_max):
            para = para.strip()
            if len(para) < min_len:
                continue
            chunks.append(
                Chunk(
                    chapter=chapter,
                    text=para,
                    topic=classify_topic(para),
                    tags=extract_tags(para),
                )
            )
    return chunks
