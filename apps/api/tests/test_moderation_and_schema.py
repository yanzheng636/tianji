"""内容审核（关键词兜底）+ 契约层 camelCase 序列化。"""

import pytest

from app.providers.moderation import KeywordModeration
from app.schemas import BirthProfileIn, CreateOrderIn, QianOut
from app.services.chat import detect_topic


@pytest.mark.asyncio
async def test_keyword_moderation_blocks():
    mod = KeywordModeration()
    ok, _ = await mod.check_text("十月考研一战上岸")
    assert ok is True

    for bad in ["加微信教你转运", "转运保证包过", "改命秘法"]:
        ok, reason = await mod.check_text(bad)
        assert ok is False
        assert reason


@pytest.mark.asyncio
async def test_keyword_moderation_ignores_spacing():
    mod = KeywordModeration()
    ok, _ = await mod.check_text("加 微 信")
    assert ok is False  # 去空格后仍命中


def test_camel_input_and_output():
    # 入参接受 camelCase
    p = BirthProfileIn(gender="female", birthDate="2003-07-13", birthHour=12)
    assert p.birth_date == "2003-07-13"
    # 入参也接受 snake_case（populate_by_name）
    p2 = BirthProfileIn(gender="male", birth_date="2000-01-01", birth_hour=None)
    assert p2.birth_date == "2000-01-01"

    # 出参序列化为 camelCase
    from datetime import datetime

    out = QianOut(
        id="x", no="第七签", level="上上", text="...", src="...", note="...",
        topic="general", drawn_at=datetime(2026, 7, 15),
    )
    dumped = out.model_dump(by_alias=True)
    assert "drawnAt" in dumped
    assert "drawn_at" not in dumped


def test_order_semantics():
    lamp = CreateOrderIn(kind="lamp", plan="year")
    lamp.validate_semantics()  # 不抛

    with pytest.raises(ValueError):
        CreateOrderIn(kind="lamp").validate_semantics()  # 缺档位

    with pytest.raises(ValueError):
        CreateOrderIn(kind="merit", amountFen=50).validate_semantics()  # 低于下限

    with pytest.raises(ValueError):
        CreateOrderIn(kind="merit", amountFen=999999).validate_semantics()  # 超上限


@pytest.mark.parametrize(
    ("query", "topic"),
    [
        ("最近身体和睡眠怎么样", "health"),
        ("想看八字日主和大运", "natal"),
        ("六爻问卦该怎样取用神", "divination"),
        ("如何改过自省、积德行善", "cultivation"),
    ],
)
def test_detect_topic_covers_all_knowledge_intents(query: str, topic: str):
    assert detect_topic(query) == topic
