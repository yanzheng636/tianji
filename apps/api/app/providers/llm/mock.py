"""Mock LLM：无需任何密钥即可跑通问卦闭环，也用于 CI。

不是简单回声——它按问题主题（升学/财运/姻缘/事业/解签）走规则，
配合服务端注入的古籍上下文，生成有「山问」人设的话术并逐字流式吐出，
体感接近真模型，方便前端联调与演示。语气与线上一致：沉静、克制、
不用网络流行语或职场黑话。
"""

from __future__ import annotations

import asyncio
import re
from collections.abc import AsyncGenerator

from app.providers.llm.base import LlmMessage

_RULES: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"解.*签|签文|这支签|签面"),
        "这支签落在你身上，说的是心里悬着的那件事——它没那么坏。"
        "签讲的是眼下的势，不是定数；势本就在你这边，剩下的，是你愿不愿意走出那一步。"
        "若想说得更细，把具体的事讲给我听。",
    ),
    (
        re.compile(r"事业|跳槽|晋升|转行|工作|升职|裁|老板|同事"),
        "你的事业眼下更像在蓄力，并没有停住。与其急着比较得失，"
        "不如先把手上的一件事，做到自己认得出的样子。"
        "我想先问问你：真正让你放不下的，是眼前这份不甘心，还是怕错过另一条路？",
    ),
    (
        re.compile(r"上岸|考研|考公|考试|升学|面试|复习|学"),
        "读书这件事，怕的从来不是不够聪明，是心太乱。你已经走了大半程，剩下的是把心放平。"
        "说说看，这份慌，是卡在某一科上，还是一想到结果就静不下来？",
    ),
    (
        re.compile(r"财|钱|富|搞钱|收入|投资|生意|副业"),
        "财这件事，稳比快要紧。眼下不必急着押上全部，也不必因为一时起落乱了分寸。"
        "你心里那份急，是真的手头紧，还是看着别人走得快、有点坐不住？",
    ),
    (
        re.compile(r"缘|爱|婚|情|喜欢|脱单|对象|暧昧|异地"),
        "感情不是断了，只是还没到。你要做的不是四处去找，而是先把自己过好。"
        "我想听听：此刻更牵动你的，是某个具体的人，还是那种一个人久了的空？",
    ),
    (
        re.compile(r"健康|身体|焦虑|失眠|累|压力|情绪"),
        "人把自己逼得太紧，气色先知道。最近先照顾好身体：睡够、按时吃饭、出门晒晒太阳。"
        "这不是玄虚，是顺序——人先安稳下来，事才跟着顺。这阵子的累，是身子累，还是心里有件事一直悬着？",
    ),
]

_DEFAULT = (
    "你的问题我收下了。答案其实常常不在远处：先把自己能掌控的那一部分做踏实，其余的交给时间。"
    "不如先跟我说说——这件事里，最让你放不下的，是哪一点？"
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
