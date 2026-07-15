"""主题与标签自动识别（关键词规则，古籍术语命中率高）。"""

from __future__ import annotations

import re

# 主题 → 触发词。命中最多者为该段主题；都不中则 general。
TOPIC_KEYWORDS: dict[str, list[str]] = {
    "exam": ["文昌", "科甲", "功名", "学业", "读书", "登科", "举", "试", "魁", "状元", "聪明"],
    "career": ["官禄", "事业", "仕", "禄", "贵人", "升", "职", "创业", "谋事", "权", "位"],
    "wealth": ["财", "禄马", "富", "money", "金银", "田宅", "商", "利", "帛", "库"],
    "love": ["姻缘", "夫妻", "婚", "情", "桃花", "红鸾", "配偶", "夫宫", "妻宫", "感情", "缘"],
    "health": ["疾", "病", "寿", "康", "气色", "精神", "养生", "命门"],
}

# 额外可抽取的标签词（用于关键词检索加权）
TAG_KEYWORDS = [
    "手相", "掌纹", "面相", "气色", "八字", "五行", "干支", "紫微", "六爻", "卦",
    "签", "吉", "凶", "生命线", "智慧线", "感情线", "文昌", "官禄", "财帛", "姻缘",
    "印堂", "明堂", "劝善", "修身", "改过", "积德",
]


def classify_topic(text: str) -> str:
    scores: dict[str, int] = {}
    for topic, words in TOPIC_KEYWORDS.items():
        scores[topic] = sum(text.count(w) for w in words)
    best = max(scores, key=lambda k: scores[k])
    return best if scores[best] > 0 else "general"


def extract_tags(text: str, limit: int = 6) -> list[str]:
    hits = [w for w in TAG_KEYWORDS if w in text]
    # 去重保序，截断
    seen: list[str] = []
    for w in hits:
        if w not in seen:
            seen.append(w)
    return seen[:limit]


# 章节标题识别：卷/篇/章/节/第…签/卦名 等
_HEADING_RE = re.compile(
    r"^\s*("
    r"卷[一二三四五六七八九十百零〇\d]+"
    r"|第[一二三四五六七八九十百零〇\d]+[章节篇卷签卦]"
    r"|[一二三四五六七八九十]+[、.．]"
    r"|[一-龥]{1,8}[篇章][：:　\s]?"
    r")"
)


def looks_like_heading(line: str) -> bool:
    s = line.strip()
    if not s:
        return False
    # 短行且无句末标点，多半是标题
    if len(s) <= 12 and not re.search(r"[。！？；]", s):
        if _HEADING_RE.match(s) or len(s) <= 6:
            return True
    return bool(_HEADING_RE.match(s))
