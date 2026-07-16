"""摇签：签谱与知识库同源 + 加密级随机 + 主题加权。"""

import re
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


def test_level_group_weights_are_valid():
    assert qian_service._LEVEL_WEIGHT_TOTAL == 100
    assert all(weight > 0 for _, weight in qian_service._LEVEL_GROUPS)


@pytest.mark.parametrize(
    ("roll", "expected"),
    [
        (0, ("大吉",)),
        (7, ("大吉",)),
        (8, ("上上",)),
        (32, ("上上",)),
        (33, ("上吉",)),
        (52, ("上吉",)),
        (53, ("中吉", "上平")),
        (69, ("中吉", "上平")),
        (70, ("中平",)),
        (94, ("中平",)),
        (95, ("下吉", "下平", "下下")),
        (99, ("下吉", "下平", "下下")),
    ],
)
def test_level_group_boundaries(
    monkeypatch: pytest.MonkeyPatch, roll: int, expected: tuple[str, ...]
):
    def fake_randbelow(total: int) -> int:
        assert total == 100
        return roll

    monkeypatch.setattr(qian_service.secrets, "randbelow", fake_randbelow)
    assert qian_service._pick_level_group() == expected


@pytest.mark.parametrize(
    ("roll", "allowed_levels"),
    [
        (0, {"大吉"}),
        (8, {"上上"}),
        (33, {"上吉"}),
        (53, {"中吉", "上平"}),
        (70, {"中平"}),
        (95, {"下吉", "下平", "下下"}),
    ],
)
def test_weighted_pick_stays_in_selected_level_group(
    monkeypatch: pytest.MonkeyPatch, roll: int, allowed_levels: set[str]
):
    rolls = iter((roll, 0))
    monkeypatch.setattr(qian_service.secrets, "randbelow", lambda _: next(rolls))
    assert _weighted_pick("love").level in allowed_levels


def test_topic_weight_only_affects_candidates_within_group(
    monkeypatch: pytest.MonkeyPatch,
):
    qians = get_qianpu()
    matched = next(q for q in qians if q.level == "上上" and "love" in q.topics)
    unmatched = next(q for q in qians if q.level == "上上" and "love" not in q.topics)
    candidates = (matched, unmatched)

    monkeypatch.setattr(qian_service.secrets, "randbelow", lambda total: total - 2)
    assert qian_service._pick_from_candidates(candidates, "love") is matched

    monkeypatch.setattr(qian_service.secrets, "randbelow", lambda total: total - 1)
    assert qian_service._pick_from_candidates(candidates, "love") is unmatched


def test_weighted_pick_rejects_missing_configured_level_group(
    monkeypatch: pytest.MonkeyPatch,
):
    incomplete_qianpu = tuple(q for q in get_qianpu() if q.level == "上上")
    monkeypatch.setattr(qian_service, "get_qianpu", lambda: incomplete_qianpu)
    monkeypatch.setattr(qian_service.secrets, "randbelow", lambda _: 0)

    with pytest.raises(AppError) as error:
        _weighted_pick(None)

    assert error.value.status_code == 503
    assert error.value.code == "QIANPU_UNAVAILABLE"


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
