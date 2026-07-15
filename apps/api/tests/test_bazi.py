"""八字排盘：真实干支四柱，非随机。"""

from app.services.bazi import compute_bazi, today_fortune_seed


def test_known_chart():
    # 2003-07-13 午时（杭州）—— 与手工核对的干支
    c = compute_bazi("2003-07-13", 12, "female")
    pillars = [f"{p.gan}{p.zhi}" for p in c.pillars]
    assert pillars == ["癸未", "己未", "丁亥", "丙午"]
    assert c.day_master.startswith("丁")
    assert c.zodiac == "羊"
    assert c.hour_known is True
    # 五行计数总和 = 8（四柱天干 + 四柱地支主气）
    assert sum(c.five_elements.values()) == 8


def test_hour_unknown_flag():
    c = compute_bazi("2000-01-01", None, "male")
    assert c.hour_known is False
    assert "时辰" in c.summary  # 摘要中标注了时辰估算


def test_deterministic():
    a = compute_bazi("1995-08-20", 8, "male")
    b = compute_bazi("1995-08-20", 8, "male")
    assert [p.gan + p.zhi for p in a.pillars] == [p.gan + p.zhi for p in b.pillars]


def test_today_fortune_seed():
    ganzhi, date_str = today_fortune_seed()
    assert ganzhi.endswith("日")
    assert len(date_str) == 10  # YYYY.MM.DD
