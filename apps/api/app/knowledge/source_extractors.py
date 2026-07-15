"""多格式古籍提取器：TXT、EPUB 与 MinerU PDF。

模块只负责把来源转换为带章节/页码的文本段，不调用项目 LLM。
"""

from __future__ import annotations

import json
import posixpath
import re
import subprocess
import zipfile
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree


@dataclass(frozen=True)
class BookSpec:
    slug: str
    name: str
    filename: str
    domain: str
    meta: str
    source_kind: str
    mineru_lang: str = "ch"
    source_relpath: str | None = None
    vertical: bool = False
    review_required: bool = False
    page_kind_overrides: tuple[tuple[int, str], ...] = ()


@dataclass
class Section:
    title: str
    lines: list[str] = field(default_factory=list)
    page: int | None = None
    quality: str = "verified"


@dataclass
class ExtractionResult:
    book: BookSpec
    sections: list[Section]
    raw_chars: int
    normalized_chars: int
    extraction: str
    page_quality: dict[int, str] = field(default_factory=dict)
    page_kinds: dict[int, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


BOOK_SPECS: tuple[BookSpec, ...] = (
    BookSpec("liaofan-sixun", "了凡四训", "了凡四训.txt", "cultivation", "修身劝善 · 明 · 袁黄", "text"),
    BookSpec(
        "bushi-zhengzong",
        "卜筮正宗",
        "modern-typeset-crosscheck.pdf",
        "divination",
        "六爻 · 清 · 王洪绪 · 完整 PDF 校勘底本",
        "pdf",
        "ch",
        "wiki_sources/bushi-zhengzong/modern-typeset-crosscheck.pdf",
        review_required=True,
    ),
    BookSpec("mingli-tanyuan", "命理探源", "命理探源.txt", "bazi", "命理 · 民国 · 袁树珊", "text"),
    BookSpec("zengguang-xianwen", "增广贤文", "增广贤文.txt", "cultivation", "蒙学格言 · 传统汇编", "text"),
    BookSpec("taishang-ganyingpian", "太上感应篇", "太上感应篇.txt", "cultivation", "劝善 · 道教典籍", "text"),
    BookSpec(
        "liuzhuang-xiangfa",
        "柳庄相法",
        "1925-wenming-shuju-qin-shenan.pdf",
        "physiognomy",
        "相法 · 明 · 1925 文明书局秦慎安校勘本",
        "pdf",
        "chinese_cht",
        "wiki_sources/liuzhuang-xiangfa/1925-wenming-shuju-qin-shenan.pdf",
        vertical=True,
        review_required=True,
    ),
    BookSpec("meihua-yishu", "梅花易数", "梅花易数.txt", "divination", "易占 · 宋 · 传邵雍", "text"),
    BookSpec("yuanhai-ziping", "渊海子平", "渊海子平.txt", "bazi", "命理 · 宋 · 徐大升", "text"),
    BookSpec("shenxiang-quanbian", "神相全编", "神相全编.txt", "physiognomy", "相法 · 传统汇编", "text"),
    BookSpec("guandi-lingqian", "關聖帝君靈籤", "關聖帝君靈籤.epub", "qian", "签谱 · 一百签", "epub"),
    BookSpec(
        "mayi-xiangfa",
        "麻衣相法",
        "NLC416-12jh002690-44091_麻衣相法_第1卷.pdf",
        "physiognomy",
        "相法 · 第一卷 · 扫描本",
        "pdf",
        "chinese_cht",
        vertical=True,
        review_required=True,
        page_kind_overrides=(
            (79, "body"),
            (80, "body"),
            (99, "body"),
            (100, "illustration"),
            (153, "back-matter"),
        ),
    ),
    BookSpec("sanming-tonghui", "三命通会", "三命通会.pdf", "bazi", "命理 · 明 · 万民英", "pdf", "ch"),
    BookSpec("qiongtong-baojian", "穷通宝鉴", "穷通宝鉴.pdf", "bazi", "命理 · 调候用神", "pdf", "ch"),
)


_LINE_NUMBER_RE = re.compile(r"^\s*\d{1,6}\s*[\t .、．]+\s*")
_MD_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$")
_EXPLICIT_HEADING_RE = re.compile(
    r"^(?:"
    r"[上下中]册|"
    r"卷[一二三四五六七八九十百零〇\d]+(?:\s+.{0,24})?|"
    r"第[一二三四五六七八九十百零〇廿卅\d]+[章节篇卷籤签卦回](?:\s+.{0,24})?|"
    r"[一二三四五六七八九十百]+[、.．]\s*.{0,24}|"
    r"[甲乙丙丁戊己庚辛壬癸]+[、.．]\s*.{0,24}"
    r")$"
)
_BRACKET_HEADING_RE = re.compile(r"^[《〈]([^》〉]{1,40})[》〉]$")
_CHINESE_ITEM_HEADING_RE = re.compile(
    r"^[一二三四五六七八九十百]{1,4}(?:取|看|观|觀|论|論|命|财|財|兄|田|男|女|奴|妻|官|疾).{1,18}$"
)
_HEADING_SUFFIXES = (
    "序", "跋", "目录", "目錄", "总论", "總論", "凡例", "篇", "章", "论", "論", "诀", "訣",
    "歌", "赋", "賦", "法", "例", "说", "說", "解", "释", "釋", "占", "断", "斷", "考",
)
_EXACT_HEADINGS = {
    "正文", "基础", "基礎", "十神", "神煞", "六亲", "六親", "五行", "天干", "地支", "纳音", "納音",
    "聖意", "圣意", "東坡解", "东坡解", "碧仙註", "碧仙注", "解曰", "釋義", "释义", "占驗", "占验",
}
_SKIP_PREFIXES = (
    "来源：", "來源：", "资源页：", "資源頁：", "正文页：", "正文頁：", "中国哲学书电子化计划",
    "中國哲學書電子化計劃", "作品 URN", "正文 URN", "URN：", "说明：", "說明：", "作者：", "成书年代：",
    "成書年代：", "版本：", "下载", "下載",
)
_SEPARATOR_RE = re.compile(r"^[=─—_\-·•＊*]{5,}$")


def normalize_text(raw: str) -> str:
    return (
        raw.replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace("\ufeff", "")
        .replace("\u200b", "")
        .replace("\u200c", "")
        .replace("\u200d", "")
        .replace("　", " ")
    )


def _clean_line(line: str) -> str:
    line = _LINE_NUMBER_RE.sub("", line.strip())
    line = re.sub(r"[ \t]+", " ", line)
    return line.strip()


def _is_book_title(line: str, book_name: str) -> bool:
    compact = re.sub(r"[《》〈〉\s]", "", line)
    target = re.sub(r"[《》〈〉\s]", "", book_name)
    return compact in {target, target.replace("關", "关").replace("靈", "灵").replace("籤", "签")}


def _is_heading(lines: list[str], index: int, previous_blank: bool) -> str | None:
    line = lines[index]
    md = _MD_HEADING_RE.match(line)
    if md:
        return md.group(1).strip()
    text = _clean_line(line).rstrip("：:")
    if not text or re.search(r"[。！？；!?]", text):
        return None
    if _EXPLICIT_HEADING_RE.match(text) or text in _EXACT_HEADINGS:
        return text
    bracket = _BRACKET_HEADING_RE.match(text)
    if bracket:
        return bracket.group(1).strip()
    if _CHINESE_ITEM_HEADING_RE.match(text):
        return text
    if len(text) <= 22 and text.endswith(_HEADING_SUFFIXES):
        return text
    next_text = ""
    for following in lines[index + 1 : index + 3]:
        next_text = _clean_line(following)
        if next_text:
            break
    if previous_blank and 1 < len(text) <= 10 and len(next_text) >= 12:
        return text
    return None


def parse_plain_sections(raw: str, book: BookSpec, default_chapter: str = "正文") -> list[Section]:
    normalized = normalize_text(raw)
    lines = normalized.split("\n")
    sections: list[Section] = []
    title = default_chapter
    body: list[str] = []
    previous_blank = True

    def flush() -> None:
        nonlocal body
        if body:
            sections.append(Section(title=title, lines=body))
            body = []

    for index, raw_line in enumerate(lines):
        cleaned = _clean_line(raw_line)
        if not cleaned:
            previous_blank = True
            continue
        if _SEPARATOR_RE.match(cleaned) or cleaned.startswith(_SKIP_PREFIXES):
            previous_blank = True
            continue
        if _is_book_title(cleaned, book.name):
            previous_blank = True
            continue
        if cleaned.startswith(book.name) and len(cleaned) <= len(book.name) + 10:
            flush()
            title = cleaned
            previous_blank = False
            continue
        heading = _is_heading(lines, index, previous_blank)
        if heading:
            flush()
            title = heading
            previous_blank = False
            continue
        body.append(cleaned)
        previous_blank = False
    flush()
    return sections


class _XHTMLBlocks(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[tuple[str, str]] = []
        self._tag: str | None = None
        self._depth = 0
        self._buf: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "svg"}:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if self._tag is None and tag in {"h1", "h2", "h3", "h4", "p", "li"}:
            self._tag = tag
            self._depth = 1
            self._buf = []
        elif self._tag is not None:
            self._depth += 1
        if tag == "br" and self._tag is not None:
            self._buf.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "svg"} and self._skip_depth:
            self._skip_depth -= 1
            return
        if self._skip_depth or self._tag is None:
            return
        self._depth -= 1
        if self._depth == 0:
            text = re.sub(r"[ \t]+", " ", "".join(self._buf))
            text = re.sub(r"\n{3,}", "\n\n", text).strip()
            if text:
                self.blocks.append((self._tag, text))
            self._tag = None
            self._buf = []

    def handle_data(self, data: str) -> None:
        if self._tag is not None and not self._skip_depth:
            self._buf.append(data)


def _epub_spine(zf: zipfile.ZipFile) -> list[str]:
    container = ElementTree.fromstring(zf.read("META-INF/container.xml"))
    rootfile = container.find(".//{*}rootfile")
    if rootfile is None or not rootfile.attrib.get("full-path"):
        raise ValueError("EPUB 缺少 rootfile")
    opf_path = rootfile.attrib["full-path"]
    opf = ElementTree.fromstring(zf.read(opf_path))
    manifest = {
        item.attrib["id"]: item.attrib["href"]
        for item in opf.findall(".//{*}manifest/{*}item")
        if item.attrib.get("id") and item.attrib.get("href")
    }
    base = posixpath.dirname(opf_path)
    ordered: list[str] = []
    for itemref in opf.findall(".//{*}spine/{*}itemref"):
        href = manifest.get(itemref.attrib.get("idref", ""))
        if href:
            ordered.append(posixpath.normpath(posixpath.join(base, href)))
    return ordered


def extract_epub(path: Path, book: BookSpec) -> ExtractionResult:
    sections: list[Section] = []
    raw_chars = 0
    with zipfile.ZipFile(path) as zf:
        for item in _epub_spine(zf):
            if any(part in item.lower() for part in ("title.xhtml", "about.xhtml", "nav.xhtml")):
                continue
            raw = zf.read(item).decode("utf-8", errors="strict")
            parser = _XHTMLBlocks()
            parser.feed(raw)
            if not any(tag in {"h1", "h2"} and re.search(r"第.+[籤簽签]", text) for tag, text in parser.blocks):
                continue
            # 与 TXT/PDF 的“可见原文字符”保持同一统计口径，不把 XHTML 标签算入分母。
            raw_chars += sum(len(text) for _, text in parser.blocks)
            top = "正文"
            sub = ""
            current: Section | None = None
            for tag, text in parser.blocks:
                if tag in {"h1", "h2"}:
                    top = text.replace("\n", " ")
                    sub = ""
                    current = Section(title=top)
                    sections.append(current)
                elif tag in {"h3", "h4"}:
                    sub = text.replace("\n", " ")
                    current = Section(title=f"{top} · {sub}")
                    sections.append(current)
                elif tag == "p" and text.rstrip("：:").strip() in _EXACT_HEADINGS:
                    sub = text.rstrip("：:").strip()
                    current = Section(title=f"{top} · {sub}")
                    sections.append(current)
                else:
                    if current is None:
                        current = Section(title=top if not sub else f"{top} · {sub}")
                        sections.append(current)
                    current.lines.extend(part.strip() for part in text.split("\n") if part.strip())
    sections = [section for section in sections if section.lines]
    return ExtractionResult(
        book=book,
        sections=sections,
        raw_chars=raw_chars,
        normalized_chars=sum(len(line) for section in sections for line in section.lines),
        extraction="epub",
    )


def extract_text(path: Path, book: BookSpec) -> ExtractionResult:
    raw = path.read_text(encoding="utf-8")
    sections = parse_plain_sections(raw, book)
    warnings: list[str] = []
    replacement_chars = raw.count("\ufffd")
    if replacement_chars:
        warnings.append(f"源文件含 {replacement_chars} 个 Unicode 替换字符，原文可能已损坏")
    trailing_fragment = re.split(r"[。！？.!?]", raw.rstrip())[-1].strip()
    if trailing_fragment and len(trailing_fragment) <= 12:
        warnings.append(f"源文件结尾疑似截断：{trailing_fragment!r}")
    return ExtractionResult(
        book=book,
        sections=sections,
        raw_chars=len(raw),
        normalized_chars=sum(len(line) for section in sections for line in section.lines),
        extraction="text",
        warnings=warnings,
    )


def _pdf_page_count(path: Path) -> int:
    result = subprocess.run(["pdfinfo", str(path)], capture_output=True, text=True, check=True)
    match = re.search(r"^Pages:\s+(\d+)", result.stdout, re.MULTILINE)
    if not match:
        raise ValueError(f"无法读取 PDF 页数：{path}")
    return int(match.group(1))


def _mineru_output_files(output_dir: Path) -> tuple[Path | None, Path | None]:
    markdown = max(output_dir.rglob("*.md"), key=lambda p: p.stat().st_size, default=None)
    content_lists = list(output_dir.rglob("*content_list.json"))
    content_list = max(content_lists, key=lambda p: p.stat().st_size, default=None)
    return markdown, content_list


def _sections_from_mineru_vertical(middle_path: Path) -> tuple[list[Section], dict[int, str]]:
    """按竖排古籍阅读顺序重排 MinerU OCR span。

    MinerU 已完成版面检测和文字识别，这里只使用其坐标产物将列从右到左排列。
    """
    payload = json.loads(middle_path.read_text(encoding="utf-8"))
    pages = payload.get("pdf_info", []) if isinstance(payload, dict) else []
    sections: list[Section] = []
    quality: dict[int, str] = {}
    for fallback_index, page_info in enumerate(pages, start=1):
        page = int(page_info.get("page_idx", fallback_index - 1)) + 1
        spans: list[tuple[float, float, float, str]] = []
        for block in page_info.get("preproc_blocks", []):
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    content = str(span.get("content") or "").strip()
                    bbox = span.get("bbox") or []
                    score = float(span.get("score") or 0)
                    if not content or len(bbox) != 4 or score < 0.55:
                        continue
                    x_center = (float(bbox[0]) + float(bbox[2])) / 2
                    y_top = float(bbox[1])
                    spans.append((x_center, y_top, score, content))
        spans.sort(key=lambda item: (-item[0], item[1]))
        lines = [item[3] for item in spans]
        cjk_chars = sum(len(re.findall(r"[\u3400-\u9fff]", line)) for line in lines)
        # 竖排古籍即使 OCR 置信度较高，也不能等同于人工校勘完成。
        # 非空页统一进入复核队列，避免把模型分数误标成“已验证”。
        status = "unusable" if cjk_chars == 0 else "review-needed"
        quality[page] = status
        if lines:
            sections.append(Section(title=f"第 {page} 页", lines=lines, page=page, quality=status))
    return sections, quality


def _sections_from_mineru_content(content_path: Path, book: BookSpec) -> tuple[list[Section], dict[int, str]]:
    payload = json.loads(content_path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("MinerU content_list 不是数组")
    sections: list[Section] = []
    current_by_page: dict[int, Section] = {}
    current_title = "正文"
    page_chars: dict[int, int] = {}
    for item in payload:
        if not isinstance(item, dict):
            continue
        page = int(item.get("page_idx", 0)) + 1
        text = str(item.get("text") or "").strip()
        if not text:
            continue
        text = normalize_text(text)
        page_chars[page] = page_chars.get(page, 0) + len(re.findall(r"[\u3400-\u9fff]", text))
        level = item.get("text_level")
        if isinstance(level, int) and 0 < level <= 4 and len(text) <= 60:
            current_title = text.replace("\n", " ")
            section = Section(title=current_title, page=page)
            sections.append(section)
            current_by_page[page] = section
            continue
        section = current_by_page.get(page)
        if section is None or section.title != current_title:
            section = Section(title=current_title, page=page)
            sections.append(section)
            current_by_page[page] = section
        section.lines.extend(_clean_line(line) for line in text.split("\n") if _clean_line(line))
    quality = {
        page: "unusable" if chars == 0 else "review-needed" if chars < 30 else "verified"
        for page, chars in page_chars.items()
    }
    for section in sections:
        section.quality = quality.get(section.page or 0, "review-needed")
    return [section for section in sections if section.lines], quality


def _classify_vertical_pages(middle_path: Path) -> dict[int, str]:
    """区分正文、插图、前后衬页、真空白页与疑似 OCR 失败页。"""
    payload = json.loads(middle_path.read_text(encoding="utf-8"))
    pages = payload.get("pdf_info", []) if isinstance(payload, dict) else []
    total = len(pages)
    kinds: dict[int, str] = {}
    for fallback_index, page_info in enumerate(pages, start=1):
        page = int(page_info.get("page_idx", fallback_index - 1)) + 1
        blocks = page_info.get("preproc_blocks", [])
        types = {str(block.get("type") or "") for block in blocks}
        contents: list[str] = []
        for block in blocks:
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    if float(span.get("score") or 0) >= 0.55:
                        contents.append(str(span.get("content") or ""))
        cjk_chars = len(re.findall(r"[\u3400-\u9fff]", "".join(contents)))
        if not blocks:
            # 版面模型没有块并不等于真空白，也可能是整页插图或印章。
            kinds[page] = "undetected"
        elif page <= 14 and cjk_chars < 30:
            kinds[page] = "front-matter"
        elif page > max(total - 3, 0) and cjk_chars < 30:
            kinds[page] = "back-matter"
        elif cjk_chars >= 8:
            kinds[page] = "body"
        elif not ({"text", "title"} & types) and ({"image", "table"} & types):
            kinds[page] = "illustration"
        else:
            kinds[page] = "ocr-failed"
    return kinds


def extract_pdf_with_mineru(
    path: Path,
    book: BookSpec,
    cache_root: Path,
    *,
    device: str = "cpu",
    source: str = "modelscope",
) -> ExtractionResult:
    output_dir = cache_root / book.slug
    output_dir.mkdir(parents=True, exist_ok=True)
    markdown, content_list = _mineru_output_files(output_dir)
    if markdown is None and content_list is None:
        command = [
            "mineru", "-p", str(path), "-o", str(output_dir), "-m", "ocr", "-b", "pipeline",
            "-l", book.mineru_lang, "-d", device, "--source", source, "-f", "false", "-t", "false",
        ]
        subprocess.run(command, check=True)
        markdown, content_list = _mineru_output_files(output_dir)
    if markdown is None and content_list is None:
        raise RuntimeError(f"MinerU 未生成可读产物：{path}")

    warnings: list[str] = []
    page_quality: dict[int, str] = {}
    page_kinds: dict[int, str] = {}
    middle_files = list(output_dir.rglob("*middle.json"))
    middle = max(middle_files, key=lambda p: p.stat().st_size, default=None)
    if book.vertical and middle is not None:
        sections, page_quality = _sections_from_mineru_vertical(middle)
        page_kinds = _classify_vertical_pages(middle)
        page_kinds.update(dict(book.page_kind_overrides))
        warnings.append("竖排扫描本已按 MinerU 坐标从右到左重排列；OCR 错字仍需抽样复核")
    elif content_list is not None:
        sections, page_quality = _sections_from_mineru_content(content_list, book)
    else:
        assert markdown is not None
        raw_md = markdown.read_text(encoding="utf-8")
        raw_md = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", raw_md)
        sections = parse_plain_sections(raw_md, book)
        warnings.append("MinerU 未提供 content_list.json，PDF 段落缺少精确页码")
    if book.review_required:
        page_quality = {
            page: "unusable" if quality == "unusable" else "review-needed"
            for page, quality in page_quality.items()
        }
        for section in sections:
            if section.quality != "unusable":
                section.quality = "review-needed"
        warnings.append("该网络/竖排底本尚未完成逐页人工校勘，证据统一标记为 review-needed")

    page_count = _pdf_page_count(path)
    for page in range(1, page_count + 1):
        page_quality.setdefault(page, "unusable")
    unusable = sum(value == "unusable" for value in page_quality.values())
    review = sum(value == "review-needed" for value in page_quality.values())
    if unusable:
        warnings.append(f"{unusable} 页没有可靠文本")
    if review:
        warnings.append(f"{review} 页需要复核")
    if page_kinds:
        kind_counts: dict[str, int] = {}
        for kind in page_kinds.values():
            kind_counts[kind] = kind_counts.get(kind, 0) + 1
        warnings.append(
            "页型分类："
            + "，".join(f"{kind} {count} 页" for kind, count in sorted(kind_counts.items()))
        )
    raw_chars = len(markdown.read_text(encoding="utf-8")) if markdown else sum(len(line) for s in sections for line in s.lines)
    return ExtractionResult(
        book=book,
        sections=sections,
        raw_chars=raw_chars,
        normalized_chars=sum(len(line) for section in sections for line in section.lines),
        extraction="mineru",
        page_quality=page_quality,
        page_kinds=page_kinds,
        warnings=warnings,
    )


def extract_book(
    book: BookSpec,
    input_dir: Path,
    mineru_cache: Path,
    *,
    mineru_device: str = "cpu",
    mineru_source: str = "modelscope",
) -> ExtractionResult:
    path = (
        input_dir.parent / book.source_relpath
        if book.source_relpath
        else input_dir / book.filename
    )
    if not path.exists():
        raise FileNotFoundError(path)
    if book.source_kind == "text":
        return extract_text(path, book)
    if book.source_kind == "epub":
        return extract_epub(path, book)
    if book.source_kind == "pdf":
        return extract_pdf_with_mineru(path, book, mineru_cache, device=mineru_device, source=mineru_source)
    raise ValueError(f"未知来源类型：{book.source_kind}")
