"""大模型 Provider 抽象。上层 service 不关心背后是 DeepSeek 还是 mock。"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Protocol, TypedDict


class LlmMessage(TypedDict):
    role: str  # system | user | assistant
    content: str


class LlmProvider(Protocol):
    name: str

    def stream(
        self,
        messages: list[LlmMessage],
        temperature: float = 0.85,
        max_tokens: int = 800,
    ) -> AsyncGenerator[str, None]:
        """流式生成，逐段 yield 文本增量。"""
        ...

    async def embed(self, texts: list[str]) -> list[list[float]] | None:
        """返回向量；不支持时返回 None（检索侧自动降级为关键词）。"""
        ...
