"""LLM Provider 工厂。按 settings.llm_provider 选择实现。"""

from __future__ import annotations

from openai import AsyncOpenAI

from app.core.config import settings
from app.providers.llm.base import LlmProvider
from app.providers.llm.mock import MockLlm
from app.providers.llm.openai_compatible import OpenAICompatibleLlm

_instance: LlmProvider | None = None


def _build_embedding_client() -> tuple[AsyncOpenAI | None, str | None]:
    if settings.embedding_provider == "openai" and settings.embedding_api_key:
        client = AsyncOpenAI(
            api_key=settings.embedding_api_key,
            base_url=settings.embedding_base_url or settings.deepseek_base_url,
        )
        return client, settings.embedding_model
    return None, None


def get_llm() -> LlmProvider:
    global _instance
    if _instance is not None:
        return _instance

    if settings.llm_provider == "deepseek":
        if not settings.deepseek_api_key:
            raise RuntimeError("LLM_PROVIDER=deepseek 但未配置 DEEPSEEK_API_KEY")
        embed_client, embed_model = _build_embedding_client()
        _instance = OpenAICompatibleLlm(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            model=settings.deepseek_model,
            embedding_client=embed_client,
            embedding_model=embed_model,
        )
    else:
        _instance = MockLlm()

    return _instance
