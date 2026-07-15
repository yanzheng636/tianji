"""八字排盘（真实干支四柱），基于 lunar_python。

不是假数据：给定公历生日 + 时辰，算出年/月/日/时四柱干支、日主、生肖、
五行分布。时辰未知时按午时估算并在结果里标注 hour_known=false。
"""

from __future__ import annotations

from datetime import datetime

from lunar_python import Solar

from app.schemas import BaziChart, BaziPillar

_WUXING = {
    "甲": "木", "乙": "木",
    "丙": "火", "丁": "火",
    "戊": "土", "己": "土",
    "庚": "金", "辛": "金",
    "壬": "水", "癸": "水",
}
# 地支藏干主气对应五行
_ZHI_WUXING = {
    "子": "水", "丑": "土", "寅": "木", "卯": "木",
    "辰": "土", "巳": "火", "午": "火", "未": "土",
    "申": "金", "酉": "金", "戌": "土", "亥": "水",
}

_ELEMENT_NOTE = {
    "木": "有生长、向上的劲，适合开拓与学习",
    "火": "热情、行动力强，注意别烧太快",
    "土": "沉稳、能扛事，是团队的地基",
    "金": "果断、有原则，利决策与执行",
    "水": "灵活、善变通，脑子转得快",
}


def compute_bazi(
    birth_date: str,
    birth_hour: int | None,
    gender: str,
) -> BaziChart:
    y, m, d = (int(x) for x in birth_date.split("-"))
    hour_known = birth_hour is not None
    hour = birth_hour if birth_hour is not None else 12  # 未知按午时

    solar = Solar.fromYmdHms(y, m, d, hour, 0, 0)
    lunar = solar.getLunar()
    ba = lunar.getEightChar()

    pillars_raw = [
        (ba.getYearGan(), ba.getYearZhi(), "年柱"),
        (ba.getMonthGan(), ba.getMonthZhi(), "月柱"),
        (ba.getDayGan(), ba.getDayZhi(), "日柱"),
        (ba.getTimeGan(), ba.getTimeZhi(), "时柱"),
    ]
    pillars = [BaziPillar(gan=g, zhi=z, label=lbl) for g, z, lbl in pillars_raw]

    # 五行统计：天干 + 地支主气
    counts = {"金": 0, "木": 0, "水": 0, "火": 0, "土": 0}
    for g, z, _ in pillars_raw:
        counts[_WUXING.get(g, "土")] += 1
        counts[_ZHI_WUXING.get(z, "土")] += 1

    day_gan = ba.getDayGan()
    day_element = _WUXING.get(day_gan, "土")
    zodiac = lunar.getYearShengXiao()

    strongest = max(counts, key=lambda k: counts[k])
    weakest = min(counts, key=lambda k: counts[k])

    summary_parts = [
        f"日主为{day_gan}（{day_element}），{_ELEMENT_NOTE.get(day_element, '')}。",
        f"命局五行以{strongest}偏旺、{weakest}偏弱；",
    ]
    if weakest != strongest:
        summary_parts.append(f"日常可多亲近{weakest}的事物来平衡（如颜色、方位、作息）。")
    if not hour_known:
        summary_parts.append("（未提供出生时辰，时柱按午时估算，仅供参考。补全时辰后更准。）")

    lunar_date = f"{lunar.getYearInChinese()}年{lunar.getMonthInChinese()}月{lunar.getDayInChinese()}"

    return BaziChart(
        pillars=pillars,
        day_master=f"{day_gan}（{day_element}）",
        zodiac=zodiac,
        lunar_date=lunar_date,
        solar_terms_note=f"节气：{lunar.getPrevJieQi().getName()} 之后",
        five_elements=counts,
        summary="".join(summary_parts),
        hour_known=hour_known,
    )


def today_fortune_seed() -> tuple[str, str]:
    """首页「今日运势」的干支日 + 日期串（真实农历/干支）。"""
    now = datetime.now()
    solar = Solar.fromYmdHms(now.year, now.month, now.day, 12, 0, 0)
    lunar = solar.getLunar()
    ganzhi_day = lunar.getDayInGanZhi()
    return f"{ganzhi_day}日", now.strftime("%Y.%m.%d")
