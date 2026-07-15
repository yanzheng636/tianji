"""DeepSeek（及任何 OpenAI 兼容协议）Provider。

用户明确要求：走 OpenAI API 协议接 DeepSeek，故直接用 openai 官方 SDK
把 base_url 指到 DeepSeek。同一套代码换 base_url + model 即可接通义/豆包等。
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from openai import AsyncOpenAI

from app.providers.llm.base import LlmMessage


class OpenAICompatibleLlm:
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        *,
        embedding_client: AsyncOpenAI | None = None,
        embedding_model: str | None = None,
    ) -> None:
        self.name = f"openai-compatible:{model}"
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self._model = model
        self._embed_client = embedding_client
        self._embed_model = embedding_model

    async def stream(
        self,
        messages: list[LlmMessage],
        temperature: float = 0.85,
        max_tokens: int = 800,
    ) -> AsyncGenerator[str, None]:
        stream = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,  # type: ignore[arg-type]
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content

    async def embed(self, texts: list[str]) -> list[list[float]] | None:
        if self._embed_client is None or self._embed_model is None:
            return None
        resp = await self._embed_client.embeddings.create(
            model=self._embed_model,
            input=texts,
        )
        return [d.embedding for d in resp.data]
