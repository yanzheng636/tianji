"""Redis：验证码存取、发码/接口频控。

连不上时降级为进程内内存实现（仅开发用，多进程不共享）。
"""

from __future__ import annotations

import time
from typing import Protocol

import redis.asyncio as aioredis

from app.core.config import settings


class KVStore(Protocol):
    async def get(self, key: str) -> str | None: ...
    async def set(self, key: str, value: str, ttl_sec: int | None = None) -> None: ...
    async def set_if_absent(self, key: str, value: str, ttl_sec: int) -> bool: ...
    async def delete(self, key: str) -> None: ...
    async def incr_with_ttl(self, key: str, ttl_sec: int) -> int: ...
    async def decrement(self, key: str) -> None: ...


class RedisStore:
    def __init__(self, client: aioredis.Redis) -> None:
        self._c = client

    async def get(self, key: str) -> str | None:
        return await self._c.get(key)

    async def set(self, key: str, value: str, ttl_sec: int | None = None) -> None:
        await self._c.set(key, value, ex=ttl_sec)

    async def set_if_absent(self, key: str, value: str, ttl_sec: int) -> bool:
        return bool(await self._c.set(key, value, ex=ttl_sec, nx=True))

    async def delete(self, key: str) -> None:
        await self._c.delete(key)

    async def incr_with_ttl(self, key: str, ttl_sec: int) -> int:
        n = await self._c.incr(key)
        if n == 1:
            await self._c.expire(key, ttl_sec)
        return int(n)

    async def decrement(self, key: str) -> None:
        await self._c.decr(key)


class MemoryStore:
    def __init__(self) -> None:
        self._m: dict[str, tuple[str, float | None]] = {}

    def _live(self, key: str) -> str | None:
        e = self._m.get(key)
        if e is None:
            return None
        v, exp = e
        if exp is not None and exp < time.time():
            self._m.pop(key, None)
            return None
        return v

    async def get(self, key: str) -> str | None:
        return self._live(key)

    async def set(self, key: str, value: str, ttl_sec: int | None = None) -> None:
        exp = time.time() + ttl_sec if ttl_sec else None
        self._m[key] = (value, exp)

    async def set_if_absent(self, key: str, value: str, ttl_sec: int) -> bool:
        if self._live(key) is not None:
            return False
        await self.set(key, value, ttl_sec)
        return True

    async def delete(self, key: str) -> None:
        self._m.pop(key, None)

    async def incr_with_ttl(self, key: str, ttl_sec: int) -> int:
        cur = int(self._live(key) or 0) + 1
        self._m[key] = (str(cur), time.time() + ttl_sec)
        return cur

    async def decrement(self, key: str) -> None:
        current = self._live(key)
        if current is None:
            return
        value = max(0, int(current) - 1)
        self._m[key] = (str(value), time.time() + 86400)


_store: KVStore | None = None


async def get_kv() -> KVStore:
    global _store
    if _store is not None:
        return _store
    try:
        client = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=1,
        )
        await client.ping()
        _store = RedisStore(client)
    except Exception:
        if settings.is_prod:
            raise RuntimeError("生产环境 Redis 不可用，拒绝使用进程内验证码存储")
        # 开发环境未起 Redis：降级内存
        _store = MemoryStore()
    return _store


def make_memory_kv() -> KVStore:
    """测试专用。"""
    return MemoryStore()
