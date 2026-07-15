"""Mock LLM：无需任何密钥即可跑通问卦闭环，也用于 CI。

不是简单回声——它按问题主题（升学/财运/姻缘/事业/解签）走规则，
配合服务端注入的古籍上下文，生成有「天机子」人设的话术并逐字流式吐出，
体感接近真模型，方便前端联调与演示。
"""

from __future__ import annotations

import asyncio
import re
from collections.abc import AsyncGenerator

from app.providers.llm.base import LlmMessage

_RULES: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"解.*签|签文|这支签|签面"),
        "此签落到你身上——心里悬着的那件事，答案偏吉。与其焦虑，不如把它拆成下一步能做的小事。"
        "签讲的是势，不是命；势已在你这边，剩下的是你走不走。想问得更细，把具体的事说来听听。",
    ),
    (
        re.compile(r"事业|跳槽|晋升|转行|工作|升职|裁|老板|同事"),
        "官禄宫扫描完毕：你的事业曲线正处在「蓄力段」，不是停滞，是加载。"
        "眼下先把手里的活儿刷成能拿得出手的代表作，跳槽窗口在秋后更稳，晋升 buff 已在路上。",
    ),
    (
        re.compile(r"上岸|考研|考公|考试|升学|面试|复习|学"),
        "卦象显示：文昌星正在你头顶加载，进度约九成。今年下半年利考试，九月前后有一波「上岸窗口期」。"
        "别慌，你不是分母——把复习节奏稳住，临场别自我怀疑。",
    ),
    (
        re.compile(r"财|钱|富|搞钱|收入|投资|生意|副业"),
        "财帛宫信号稳定：正财平稳，偏财有波动。建议别 all in，分批定投你的运气。"
        "农历十月后财路带宽扩容，届时该出手时别犹豫。",
    ),
    (
        re.compile(r"缘|爱|婚|情|喜欢|脱单|对象|暧昧|异地"),
        "感情线深而清晰、末端上扬——姻缘服务器没宕机，只是在排队。"
        "缘分预计一两个版本内上线，你要做的是保持自身发光，别为还没出现的人提前内耗。",
    ),
    (
        re.compile(r"健康|身体|焦虑|失眠|累|压力|情绪"),
        "印堂气色是所有运势的底层带宽。最近你把自己跑得太满了，"
        "先补觉、先吃饭、先出门晒十分钟太阳——状态一亮，诸事自顺。这不是玄学，是顺序。",
    ),
]

_DEFAULT = (
    "已接收你的问题，天机推演中……本座翻了三卷古籍，结论是：稳。"
    "心之所向，即是吉方。眼下别急着要一个确定答案，先把能掌控的那部分做扎实，"
    "剩下的交给时间。想要更准的推演，可去「我的命盘」补全生辰。"
)


def _reply_for(user_text: str) -> str:
    for pat, reply in _RULES:
        if pat.search(user_text):
            return reply
    return _DEFAULT


class MockLlm:
    name = "mock"

    async def stream(
        self,
        messages: list[LlmMessage],
        temperature: float = 0.85,
        max_tokens: int = 800,
    ) -> AsyncGenerator[str, None]:
        user_text = ""
        for m in reversed(messages):
            if m["role"] == "user":
                user_text = m["content"]
                break
        reply = _reply_for(user_text)
        # 逐字流式，模拟打字
        for ch in reply:
            yield ch
            await asyncio.sleep(0.012)

    async def embed(self, texts: list[str]) -> list[list[float]] | None:
        return None  # 走关键词检索降级
