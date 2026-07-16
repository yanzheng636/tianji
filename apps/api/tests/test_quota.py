from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.core.errors import AppError
from app.services import quota


class FakeDb:
    def __init__(self, scalar_result: int | None = None) -> None:
        self.scalar_result = scalar_result
        self.scalar_calls = 0
        self.execute_calls = 0
        self.commit_calls = 0

    async def scalar(self, _statement: Any) -> int | None:
        self.scalar_calls += 1
        return self.scalar_result

    async def execute(self, _statement: Any) -> None:
        self.execute_calls += 1

    async def commit(self) -> None:
        self.commit_calls += 1


def test_qian_limit_rejects_negative_configuration():
    with pytest.raises(ValidationError):
        Settings(qian_daily_limit=-1)


@pytest.mark.asyncio
async def test_unlimited_qian_quota_skips_database(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(quota.settings, "qian_daily_limit", 0)
    db = FakeDb()

    current = await quota.get_quota(db, "user-1", "qian")  # type: ignore[arg-type]
    consumed = await quota.consume(db, "user-1", "qian")  # type: ignore[arg-type]

    assert current.unlimited is True
    assert consumed.unlimited is True
    assert current.limit == current.remaining == 0
    assert db.scalar_calls == db.execute_calls == db.commit_calls == 0


@pytest.mark.asyncio
async def test_positive_qian_limit_keeps_existing_counter(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(quota.settings, "qian_daily_limit", 3)
    db = FakeDb(scalar_result=2)

    current = await quota.get_quota(db, "user-1", "qian")  # type: ignore[arg-type]
    consumed = await quota.consume(db, "user-1", "qian")  # type: ignore[arg-type]

    assert current.model_dump() == {
        "kind": "qian",
        "used": 2,
        "limit": 3,
        "remaining": 1,
        "unlimited": False,
    }
    assert consumed.used == 2
    assert consumed.remaining == 1
    assert db.scalar_calls == 2
    assert db.commit_calls == 1


@pytest.mark.asyncio
async def test_positive_qian_limit_still_rejects_overage(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(quota.settings, "qian_daily_limit", 3)
    db = FakeDb(scalar_result=4)

    with pytest.raises(AppError) as error:
        await quota.consume(db, "user-1", "qian")  # type: ignore[arg-type]

    assert error.value.status_code == 429
    assert db.execute_calls == 1
    assert db.commit_calls == 1
