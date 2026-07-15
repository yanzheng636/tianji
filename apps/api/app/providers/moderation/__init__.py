"""内容审核 Provider。

许愿池是 UGC，大陆上线**法定必须**审。
- keyword：内置敏感词表，本地/开发用（兜底，绝不能当唯一防线）
- aliyun：阿里云内容安全（文本反垃圾），上线用

返回 (passed, reason)。
"""

from __future__ import annotations

import logging
from typing import Protocol

from app.core.config import settings

logger = logging.getLogger("tianji.moderation")


class ModerationProvider(Protocol):
    async def check_text(self, text: str) -> tuple[bool, str | None]: ...


# 极简内置词表：政治敏感/涉黄涉暴/辱骂/联系方式引流。仅兜底。
_BLOCK_WORDS = [
    # 联系方式引流（算命类高发导流场景）
    "加微信", "加v", "私聊", "扫码", "vx", "威信", "薇信",
    # 辱骂/暴力（示例）
    "傻逼", "去死", "杀了",
    # 涉黄（示例）
    "约炮", "裸聊",
    # 诈骗/迷信过度承诺（合规红线：不得承诺改命）
    "包过", "转运保证", "改命",
]


class KeywordModeration:
    async def check_text(self, text: str) -> tuple[bool, str | None]:
        low = text.lower().replace(" ", "")
        for w in _BLOCK_WORDS:
            if w.lower() in low:
                return False, "包含不当内容"
        return True, None


class AliyunModeration:
    def __init__(self) -> None:
        if not (
            settings.aliyun_green_access_key_id and settings.aliyun_green_access_key_secret
        ):
            raise RuntimeError("MODERATION_PROVIDER=aliyun 但阿里云内容安全配置不完整")

    async def check_text(self, text: str) -> tuple[bool, str | None]:  # pragma: no cover
        # TODO: 接入阿里云内容安全 TextModeration（green-cip）。
        # 失败时应 fail-safe：审核服务不可用 => 标记 pending 人工复核，而非直接放行。
        logger.info("[aliyun-moderation] 占位，未真实调用")
        raise NotImplementedError("阿里云内容安全需接入后启用")


_instance: ModerationProvider | None = None


def get_moderation() -> ModerationProvider:
    global _instance
    if _instance is None:
        _instance = (
            AliyunModeration()
            if settings.moderation_provider == "aliyun"
            else KeywordModeration()
        )
    return _instance
