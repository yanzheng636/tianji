"""摇签：加密级随机 + 主题加权。"""

from collections import Counter

from app.data.qians import QIAN_BY_SLUG, QIANS
from app.services.qian import _weighted_pick


def test_all_qians_have_required_fields():
    for q in QIANS:
        assert q["slug"] and q["no"] and q["level"] and q["text"]
        assert q["src"] and q["note"]
        assert q["topic"] in {"general", "exam", "love", "wealth", "career"}


def test_slug_unique():
    slugs = [q["slug"] for q in QIANS]
    assert len(slugs) == len(set(slugs))
    assert set(QIAN_BY_SLUG.keys()) == set(slugs)


def test_weighted_pick_biases_topic():
    # 大样本下，指定主题的签出现频率应显著高于其在全表的占比
    n = 4000
    counts = Counter(_weighted_pick("wealth")["topic"] for _ in range(n))
    wealth_ratio = counts["wealth"] / n
    base_ratio = sum(1 for q in QIANS if q["topic"] == "wealth") / len(QIANS)
    assert wealth_ratio > base_ratio  # 加权确实提升了命中率


def test_weighted_pick_always_valid():
    for _ in range(200):
        q = _weighted_pick(None)
        assert q in QIANS
