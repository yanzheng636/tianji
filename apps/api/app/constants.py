"""业务常量。金额一律用「分」为单位，避免浮点误差。

前端 apps/web/src/shared.ts 里有一份对应镜像，改动需两边同步。
"""

from __future__ import annotations

from typing import Literal, TypedDict

HallKey = Literal["wenshu", "yuelao", "caishen", "tianji", "qianfang"]
QianTopic = Literal["general", "exam", "love", "wealth", "career"]
IncenseType = Literal["tan", "chen", "dian"]
LampPlan = Literal["month", "year", "eternal"]

HALL_KEYS: list[HallKey] = ["wenshu", "yuelao", "caishen", "tianji", "qianfang"]
QIAN_TOPICS: list[QianTopic] = ["general", "exam", "love", "wealth", "career"]
INCENSE_TYPES: list[IncenseType] = ["tan", "chen", "dian"]
LAMP_PLANS: list[LampPlan] = ["month", "year", "eternal"]


class HallMeta(TypedDict):
    key: str
    name: str
    code: str
    char: str
    deity: str
    sub: str
    desc: str
    topic: str


HALLS: dict[str, HallMeta] = {
    "wenshu": {
        "key": "wenshu",
        "name": "文殊殿",
        "code": "HALL-01",
        "char": "文",
        "deity": "文殊菩萨",
        "sub": "WISDOM MODULE · 文昌位已校准",
        "desc": "主管升学、考试、智慧加持。考研考公、期末逆袭、面试开光，皆可在此殿求问。",
        "topic": "exam",
    },
    "yuelao": {
        "key": "yuelao",
        "name": "月老祠",
        "code": "HALL-02",
        "char": "缘",
        "deity": "月下老人",
        "sub": "MATCH ENGINE · 红线库存充足",
        "desc": "主管姻缘、感情、桃花。单身求脱单、暧昧求进展、异地求安心，红线由此牵出。",
        "topic": "love",
    },
    "caishen": {
        "key": "caishen",
        "name": "财神殿",
        "code": "HALL-03",
        "char": "财",
        "deity": "赵公明元帅",
        "sub": "WEALTH DAEMON · 财帛宫监听中",
        "desc": "主管财运、事业、偏财。搞钱、跳槽、晋升、副业开张，先来此殿报个备。",
        "topic": "wealth",
    },
    "tianji": {
        "key": "tianji",
        "name": "天机殿",
        "code": "HALL-00",
        "char": "机",
        "deity": "天机子本尊",
        "sub": "CORE TEMPLE · 本命数据中心",
        "desc": "本寺主殿。八字排盘、本命推演，你的命盘底层数据都在这里生成。",
        "topic": "general",
    },
    "qianfang": {
        "key": "qianfang",
        "name": "签房",
        "code": "HALL-04",
        "char": "签",
        "deity": "天机签房",
        "sub": "ORACLE ROOM · 随机数由天注定",
        "desc": "本寺解签处。摇签问事，大师坐堂解签；有疑再问，不限追问。",
        "topic": "general",
    },
}


class IncenseMeta(TypedDict):
    key: str
    char: str
    name: str
    desc: str
    duration_sec: int


INCENSES: dict[str, IncenseMeta] = {
    "tan": {"key": "tan", "char": "檀", "name": "檀香", "desc": "静心 · 解精神内耗", "duration_sec": 30 * 60},
    "chen": {"key": "chen", "char": "沉", "name": "沉香", "desc": "求财 · 招贵人", "duration_sec": 30 * 60},
    "dian": {"key": "dian", "char": "电", "name": "电子高香", "desc": "赛博特供 · 零明火零 PM2.5", "duration_sec": 30 * 60},
}


class LampPlanMeta(TypedDict):
    key: str
    name: str
    price_fen: int
    days: int | None
    recommended: bool


LAMP_PLAN_META: dict[str, LampPlanMeta] = {
    "month": {"key": "month", "name": "月灯", "price_fen": 1800, "days": 30, "recommended": False},
    "year": {"key": "year", "name": "年灯", "price_fen": 9800, "days": 365, "recommended": True},
    "eternal": {"key": "eternal", "name": "长明", "price_fen": 29800, "days": None, "recommended": False},
}

# 随喜功德（打赏）：服务端只认区间，防篡改
MERIT_MIN_FEN = 100
MERIT_MAX_FEN = 20000
MERIT_PRESETS_FEN = [168, 666, 888]

# 免费额度（每日）
FREE_QUOTA = {"qian": 3, "chat": 10}
LAMP_QUOTA = {"qian": 20, "chat": 200}

# 文本长度上限
WISH_MAX_LENGTH = 60
CHAT_MAX_LENGTH = 500

DISCLAIMER = (
    "本产品为传统文化娱乐与心理疗愈内容，所有解读均由 AI 生成，"
    "不构成任何医疗、法律、投资或人生决策建议。"
)
