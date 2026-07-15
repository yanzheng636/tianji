"""藏经阁语料（RAG 溯源库）。

大师引用的每一句，都能在这里翻到原文——「不玄乎，可溯源」。
seed 时写入 DB；问卦服务按主题/关键词检索，把命中的原文作为 citation 附在回答里。
"""

from __future__ import annotations

from typing import TypedDict


class PassageSeed(TypedDict):
    chapter: str
    text: str
    plain: str
    topic: str


class BookSeed(TypedDict):
    slug: str
    char: str
    name: str
    meta: str
    passages: list[PassageSeed]


BOOKS: list[BookSeed] = [
    {
        "slug": "mayi",
        "char": "相",
        "name": "麻衣相法",
        "meta": "相法 · 三卷 · 宋",
        "passages": [
            {
                "chapter": "卷二 · 掌纹篇",
                "text": "掌有三奇纹，主贵；明堂平满，财帛自聚。",
                "plain": "掌心开阔平满，是聚财的手相。",
                "topic": "wealth",
            },
            {
                "chapter": "卷三 · 官禄篇",
                "text": "官禄宫丰隆者，事业有成，贵人自来。",
                "plain": "官禄宫饱满的人，事业顺，常遇贵人。",
                "topic": "career",
            },
            {
                "chapter": "卷一 · 气色篇",
                "text": "印堂明润，诸事亨通；晦暗则百事多阻。",
                "plain": "状态好、气色亮的时候做事顺；状态差就先别硬撑。",
                "topic": "general",
            },
        ],
    },
    {
        "slug": "liuzhuang",
        "char": "柳",
        "name": "柳庄相法",
        "meta": "相法 · 两卷 · 明",
        "passages": [
            {
                "chapter": "下篇 · 情纹",
                "text": "感情线明润者，情深而专。",
                "plain": "感情线清晰润泽的人，用情深而专一。",
                "topic": "love",
            },
            {
                "chapter": "下篇 · 气色",
                "text": "神清气朗，百忧自解。",
                "plain": "精神清爽的时候，很多烦恼会自己消解——先把自己养亮。",
                "topic": "general",
            },
        ],
    },
    {
        "slug": "yuanhai",
        "char": "命",
        "name": "渊海子平",
        "meta": "命理 · 五卷 · 宋",
        "passages": [
            {
                "chapter": "卷四 · 文昌",
                "text": "文昌入命，主聪明而利科甲。",
                "plain": "文昌星入命，头脑聪明，利于考试功名。",
                "topic": "exam",
            },
            {
                "chapter": "卷一 · 论财",
                "text": "财星得地，富自天来；身旺任财，方能享用。",
                "plain": "财运好还得自身扛得住，身体和心态是本金。",
                "topic": "wealth",
            },
            {
                "chapter": "卷三 · 论官",
                "text": "官星清正，官位显达；忌见伤官夺之。",
                "plain": "事业运正的时候容易出头，最怕自己乱来把好局搅了。",
                "topic": "career",
            },
        ],
    },
    {
        "slug": "zhouyi",
        "char": "易",
        "name": "周易",
        "meta": "易占 · 两卷 · 先秦",
        "passages": [
            {
                "chapter": "系辞上",
                "text": "善易者不卜，心诚则灵。",
                "plain": "真正懂易的人不迷卜卦——诚心与行动才是关键。",
                "topic": "general",
            },
            {
                "chapter": "乾 · 象传",
                "text": "天行健，君子以自强不息。",
                "plain": "天道运转不停，人也该不断向前——最灵的签是这句。",
                "topic": "general",
            },
            {
                "chapter": "泰 · 彖传",
                "text": "天地交而万物通，上下交而其志同。",
                "plain": "上下顺、内外通的时候诸事顺遂；先把关系理顺，事就成了。",
                "topic": "career",
            },
        ],
    },
    {
        "slug": "lingqian",
        "char": "签",
        "name": "关帝灵签",
        "meta": "签谱 · 一百签 · 清",
        "passages": [
            {
                "chapter": "第七签 · 上上",
                "text": "云开月出正分明，不须进退问前程。",
                "plain": "云散月明，前路已亮，别再犹豫。",
                "topic": "general",
            },
            {
                "chapter": "第廿三签 · 上吉",
                "text": "宝剑出匣耀光明，在匣全然不惹尘。",
                "plain": "是把好剑就该出鞘，机会属于敢亮相的人。",
                "topic": "career",
            },
            {
                "chapter": "第六十一签 · 上吉",
                "text": "石藏无价玉，只待有缘人。",
                "plain": "你的价值在等对的人看见，别急着将就。",
                "topic": "love",
            },
        ],
    },
]
