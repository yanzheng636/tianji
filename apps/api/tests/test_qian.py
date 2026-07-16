"""摇签：签谱与知识库同源 + 加密级随机 + 主题加权。"""

import re
from collections import Counter
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.errors import AppError
from app.knowledge.qianpu import get_qianpu, qian_by_slug
from app.models import QianDraw, User
from app.providers.llm.mock import MockLlm
from app.routers import qian as qian_router
from app.schemas import SaveQianIn
from app.services import qian as qian_service
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


@pytest_asyncio.fixture
async def qian_db() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(User.__table__.create)
        await connection.run_sync(QianDraw.__table__.create)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


async def _seed_draws(db: AsyncSession) -> tuple[User, User, list[QianDraw]]:
    owner = User(phone="13800000001", nickname="甲")
    other = User(phone="13800000002", nickname="乙")
    db.add_all([owner, other])
    await db.flush()
    now = datetime.now(UTC)
    rows = [
        QianDraw(
            user_id=owner.id,
            hall="qianfang",
            topic="general",
            qian_slug="gd-07",
            saved=False,
            created_at=now - timedelta(minutes=2),
        ),
        QianDraw(
            user_id=owner.id,
            hall="wenshu",
            topic="exam",
            qian_slug="gd-13",
            saved=True,
            created_at=now,
        ),
        QianDraw(
            user_id=other.id,
            hall="yuelao",
            topic="love",
            qian_slug="gd-19",
            saved=True,
            created_at=now + timedelta(minutes=1),
        ),
    ]
    db.add_all(rows)
    await db.commit()
    return owner, other, rows


@pytest.mark.asyncio
async def test_save_unsave_and_saved_list_only_returns_owned_saved(qian_db: AsyncSession):
    owner, _, rows = await _seed_draws(qian_db)

    assert await qian_service.set_saved(qian_db, owner.id, rows[0].id, True) is True
    saved = await qian_service.list_saved(qian_db, owner.id)
    assert [item.id for item in saved] == [rows[1].id, rows[0].id]
    assert all(item.saved for item in saved)

    assert await qian_service.set_saved(qian_db, owner.id, rows[1].id, False) is False
    saved = await qian_service.list_saved(qian_db, owner.id)
    assert [item.id for item in saved] == [rows[0].id]


@pytest.mark.asyncio
async def test_other_users_draw_is_reported_as_404(qian_db: AsyncSession):
    owner, other, rows = await _seed_draws(qian_db)
    with pytest.raises(AppError) as save_error:
        await qian_router.save_qian(
            rows[0].id, SaveQianIn(saved=True), user=other, db=qian_db
        )
    assert save_error.value.status_code == 404

    with pytest.raises(AppError) as reading_error:
        await qian_router.reading(rows[2].id, user=owner, db=qian_db)
    assert reading_error.value.status_code == 404


@pytest.mark.asyncio
async def test_mock_reading_has_stable_reflective_structure(
    qian_db: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    owner, _, rows = await _seed_draws(qian_db)

    async def no_chart(_db: AsyncSession, _user_id: str):
        return None

    monkeypatch.setattr(qian_service.profile, "get_chart", no_chart)
    monkeypatch.setattr(qian_service, "get_llm", lambda: MockLlm())
    events = [
        event async for event in qian_service.interpret(qian_db, owner.id, rows[0].id)
    ]
    text = "".join(event.get("text", "") for event in events)
    assert [event["type"] for event in events] == ["delta", "done"]
    assert "今日可做" in text
    assert "心若从容" in text
    assert "预测" not in text


@pytest.mark.asyncio
async def test_real_provider_short_reply_gets_action_and_closing_fallback(
    qian_db: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    owner, _, rows = await _seed_draws(qian_db)

    class ShortLlm:
        name = "openai-compatible:test"

        async def stream(self, *_args, **_kwargs):
            yield "你正站在需要慢一点看清心意的时刻。"

    async def no_chart(_db: AsyncSession, _user_id: str):
        return None

    monkeypatch.setattr(qian_service.profile, "get_chart", no_chart)
    monkeypatch.setattr(qian_service, "get_llm", lambda: ShortLlm())
    events = [
        event async for event in qian_service.interpret(qian_db, owner.id, rows[0].id)
    ]
    text = "".join(event.get("text", "") for event in events)
    assert "今日可做" in text
    assert text.count("\n") >= 2
    assert events[-1]["type"] == "done"
