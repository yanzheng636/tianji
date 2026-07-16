"""个人愿池的数据隔离、计数与还愿行为。"""

from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models import User, Wish
from app.services import wish as wish_service


@pytest_asyncio.fixture
async def wish_db() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(User.__table__.create)
        await connection.run_sync(Wish.__table__.create)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


async def _seed_wishes(db: AsyncSession) -> tuple[User, User, list[Wish]]:
    owner = User(phone="13800000011", nickname="甲")
    other = User(phone="13800000012", nickname="乙")
    db.add_all([owner, other])
    await db.flush()
    now = datetime.now(UTC)
    rows = [
        Wish(
            user_id=owner.id,
            text="愿我认真开始新的生活",
            status="active",
            moderation="approved",
            created_at=now,
        ),
        Wish(
            user_id=owner.id,
            text="愿我记得第一次独自远行",
            status="fulfilled",
            moderation="rejected",
            created_at=now - timedelta(days=1),
            fulfilled_at=now,
        ),
        Wish(
            user_id=other.id,
            text="不应出现在甲的愿池",
            status="active",
            moderation="approved",
            created_at=now + timedelta(minutes=1),
        ),
    ]
    db.add_all(rows)
    await db.commit()
    return owner, other, rows


@pytest.mark.asyncio
async def test_pool_only_returns_the_current_users_wishes(wish_db: AsyncSession):
    owner, _, rows = await _seed_wishes(wish_db)

    result = await wish_service.pool(wish_db, owner.id)

    assert result.total == 2
    assert result.floating == []
    assert [wish.id for wish in result.mine] == [rows[0].id, rows[1].id]
    assert all(wish.mine for wish in result.mine)
    assert {wish.moderation for wish in result.mine} == {"approved", "rejected"}


@pytest.mark.asyncio
async def test_pool_without_a_user_never_exposes_wishes(wish_db: AsyncSession):
    await _seed_wishes(wish_db)

    result = await wish_service.pool(wish_db, None)

    assert result.total == 0
    assert result.floating == []
    assert result.mine == []


@pytest.mark.asyncio
async def test_fulfilled_wish_remains_in_personal_history(wish_db: AsyncSession):
    owner, _, rows = await _seed_wishes(wish_db)

    fulfilled = await wish_service.fulfill(wish_db, owner.id, rows[0].id)
    result = await wish_service.pool(wish_db, owner.id)

    assert fulfilled.status == "fulfilled"
    assert fulfilled.fulfilled_at is not None
    assert result.total == 2
    assert {wish.id for wish in result.mine} == {rows[0].id, rows[1].id}
