"""摇签：签谱与知识库同源 + 加密级随机 + 主题加权。"""

import re
from collections import Counter

from app.knowledge.qianpu import get_qianpu, qian_by_slug
from app.services.qian import _weighted_pick

# 切换签谱前数据库里已有的抽签记录 slug，必须永远可解析
_LEGACY_SLUGS = [
    "gd-04", "gd-07", "gd-13", "gd-19", "gd-23", "gd-30",
    "gd-36", "gd-41", "gd-44", "gd-53", "gd-61", "gd-88",
]

_POEM_RE = re.compile(r"^.{7}，.{7}。.{7}，.{7}。$")


def test_qianpu_covers_all_hundred_qians():
    qians = get_qianpu()
    assert len(qians) == 100
    assert [q.number for q in qians] == list(range(1, 101))


def test_all_qians_have_required_fields():
    for q in get_qianpu():
        assert q.slug and q.no and q.level and q.text
        assert q.src and q.note and q.source_path
        assert q.topics  # 图谱为每支签标注了意图


def test_poems_come_from_the_source_scripture():
    qians = get_qianpu()
    # 签诗为原典七言四句（解析失败时保留原文，允许极少数例外）
    formatted = [q for q in qians if _POEM_RE.match(q.text)]
    assert len(formatted) == 100
    # 抽查：第七签是吕洞宾炼丹，与 knowledge_wiki 的原典一致
    q7 = qian_by_slug("gd-07")
    assert q7 is not None
    assert q7.no == "第七签"
    assert q7.level == "大吉"
    assert q7.story == "呂洞賓煉丹"
    assert q7.text.startswith("仙風道骨本天生")


def test_slug_unique_and_legacy_slugs_still_resolve():
    qians = get_qianpu()
    slugs = [q.slug for q in qians]
    assert len(slugs) == len(set(slugs))
    for slug in _LEGACY_SLUGS:
        assert qian_by_slug(slug) is not None


def test_weighted_pick_biases_topic():
    # 大样本下，指定主题的签出现频率应显著高于其在全表的占比。
    # 用 love 检验：原典签谱里约半数签标注姻缘意图，加权才有区分度
    # （wealth/career 等意图几乎每签都有，无从观察偏置）。
    n = 4000
    qians = get_qianpu()
    counts = Counter("love" in _weighted_pick("love").topics for _ in range(n))
    love_ratio = counts[True] / n
    base_ratio = sum(1 for q in qians if "love" in q.topics) / len(qians)
    assert love_ratio > base_ratio  # 加权确实提升了命中率


def test_weighted_pick_always_valid():
    qians = get_qianpu()
    for _ in range(200):
        assert _weighted_pick(None) in qians
