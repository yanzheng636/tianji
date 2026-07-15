"""Pydantic v2 请求 / 响应模型 —— API 契约。"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel

from app.constants import (
    CHAT_MAX_LENGTH,
    HALL_KEYS,
    INCENSE_TYPES,
    LAMP_PLANS,
    MERIT_MAX_FEN,
    MERIT_MIN_FEN,
    QIAN_TOPICS,
    WISH_MAX_LENGTH,
)

PHONE_RE = re.compile(r"^1[3-9]\d{9}$")


class CamelModel(BaseModel):
    """全站基类：对外走 camelCase（JS 友好），对内仍用 snake_case。
    输入同时接受 camelCase 与 snake_case；输出统一 camelCase。
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


# 兼容旧引用
ORMModel = CamelModel


# ── 认证 ──
class SendCodeIn(CamelModel):
    phone: str

    @field_validator("phone")
    @classmethod
    def _phone(cls, v: str) -> str:
        if not PHONE_RE.match(v):
            raise ValueError("请输入有效的手机号")
        return v


class LoginIn(CamelModel):
    phone: str
    code: str

    @field_validator("phone")
    @classmethod
    def _phone(cls, v: str) -> str:
        if not PHONE_RE.match(v):
            raise ValueError("请输入有效的手机号")
        return v

    @field_validator("code")
    @classmethod
    def _code(cls, v: str) -> str:
        if not re.match(r"^\d{6}$", v):
            raise ValueError("验证码为 6 位数字")
        return v


class UserOut(CamelModel):
    id: str
    phone: str
    nickname: str | None
    is_lamp: bool = False


class AuthOut(CamelModel):
    token: str
    user: UserOut


# ── 命盘 / 八字 ──
class BirthProfileIn(CamelModel):
    nickname: str | None = Field(default=None, max_length=20)
    gender: Literal["male", "female"]
    birth_date: str
    birth_hour: int | None = Field(default=None, ge=0, le=23)
    birth_place: str | None = Field(default=None, max_length=40)

    @field_validator("birth_date")
    @classmethod
    def _date(cls, v: str) -> str:
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", v):
            raise ValueError("日期格式应为 YYYY-MM-DD")
        return v


class BaziPillar(CamelModel):
    gan: str
    zhi: str
    label: str  # 年柱/月柱/日柱/时柱


class BaziChart(CamelModel):
    pillars: list[BaziPillar]
    day_master: str  # 日主（日干）
    zodiac: str  # 生肖
    lunar_date: str
    solar_terms_note: str
    five_elements: dict[str, int]  # 金木水火土 计数
    summary: str
    hour_known: bool


# ── 摇签 ──
class DrawQianIn(CamelModel):
    hall: str = "qianfang"
    topic: str | None = None

    @field_validator("hall")
    @classmethod
    def _hall(cls, v: str) -> str:
        if v not in HALL_KEYS:
            raise ValueError("未知的殿")
        return v

    @field_validator("topic")
    @classmethod
    def _topic(cls, v: str | None) -> str | None:
        if v is not None and v not in QIAN_TOPICS:
            raise ValueError("未知的主题")
        return v


class QianOut(CamelModel):
    id: str
    no: str
    level: str
    text: str
    src: str
    note: str
    topic: str
    drawn_at: datetime


class QuotaOut(CamelModel):
    kind: str
    used: int
    limit: int
    remaining: int


# ── 上香 ──
class LightIncenseIn(CamelModel):
    type: str
    wish: str | None = Field(default=None, max_length=WISH_MAX_LENGTH)

    @field_validator("type")
    @classmethod
    def _type(cls, v: str) -> str:
        if v not in INCENSE_TYPES:
            raise ValueError("未知的香型")
        return v


class IncenseOut(CamelModel):
    id: str
    type: str
    name: str
    started_at: datetime
    ends_at: datetime
    duration_sec: int
    remaining_sec: int
    status: Literal["burning", "done"]


# ── 许愿池 ──
class CreateWishIn(CamelModel):
    text: str = Field(min_length=1, max_length=WISH_MAX_LENGTH)

    @field_validator("text")
    @classmethod
    def _trim(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("写点什么再投币吧")
        return v


class WishOut(CamelModel):
    id: str
    text: str
    status: Literal["active", "fulfilled"]
    # 审核状态：approved 进公共池；pending/rejected 仅本人可见
    moderation: Literal["pending", "approved", "rejected"] = "approved"
    moderation_reason: str | None = None
    created_at: datetime
    fulfilled_at: datetime | None
    mine: bool


class WishPoolOut(CamelModel):
    total: int
    floating: list[WishOut]  # 公共池随机漂浮
    mine: list[WishOut]


# ── 问卦 ──
class ChatIn(CamelModel):
    text: str = Field(min_length=1, max_length=CHAT_MAX_LENGTH)
    qian_id: str | None = None

    @field_validator("text")
    @classmethod
    def _trim(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("说点什么吧")
        return v


class CitationOut(CamelModel):
    book: str
    chapter: str
    text: str
    plain: str
    source_id: str | None = None
    quality: Literal["verified", "review-needed", "unusable"] = "verified"
    concepts: list[str] = Field(default_factory=list)
    intent: str | None = None
    path: str | None = None
    relation_hops: list[str] = Field(default_factory=list)
    structure: dict[str, object] | None = None


class ChatMessageOut(CamelModel):
    id: str
    role: Literal["user", "assistant"]
    text: str
    citation: CitationOut | None
    created_at: datetime


# ── 藏经阁 ──
class BookSummaryOut(CamelModel):
    slug: str
    char: str
    name: str
    meta: str
    passage_count: int


class PassageOut(CamelModel):
    id: str
    chapter: str
    text: str
    plain: str


class BookDetailOut(BookSummaryOut):
    passages: list[PassageOut]


# ── 藏经阁 · 命理百科（知识图谱浏览层）──
class WikiBookRefOut(CamelModel):
    slug: str
    name: str
    meta: str


class WikiDomainSummaryOut(CamelModel):
    slug: str
    name: str
    char: str
    description: str
    concept_count: int
    passage_count: int
    books: list[WikiBookRefOut] = Field(default_factory=list)


class WikiConceptRefOut(CamelModel):
    id: str
    name: str
    definition: str
    intents: list[str] = Field(default_factory=list)
    evidence_count: int


class WikiDomainDetailOut(CamelModel):
    slug: str
    name: str
    char: str
    description: str
    concept_count: int
    passage_count: int
    concepts: list[WikiConceptRefOut] = Field(default_factory=list)
    books: list[WikiBookRefOut] = Field(default_factory=list)


class WikiEvidenceOut(CamelModel):
    source_id: str
    book: str
    chapter: str
    text: str
    quality: Literal["verified", "review-needed", "unusable"] = "verified"
    path: str = ""


class WikiRelatedConceptOut(CamelModel):
    id: str
    name: str
    relation: str


class WikiConceptDetailOut(CamelModel):
    id: str
    name: str
    domain: str
    domain_name: str
    definition: str
    aliases: list[str] = Field(default_factory=list)
    intents: list[str] = Field(default_factory=list)
    status: Literal["verified", "review-needed", "unusable"] = "verified"
    evidence: list[WikiEvidenceOut] = Field(default_factory=list)
    evidence_total: int = 0
    related: list[WikiRelatedConceptOut] = Field(default_factory=list)


class WikiConceptHitOut(CamelModel):
    id: str
    name: str
    domain: str
    domain_name: str
    definition: str
    evidence_count: int


class WikiPassageHitOut(CamelModel):
    book: str
    chapter: str
    text: str
    quality: Literal["verified", "review-needed", "unusable"] = "verified"
    source_id: str | None = None
    path: str = ""
    concepts: list[str] = Field(default_factory=list)


class WikiSearchOut(CamelModel):
    concepts: list[WikiConceptHitOut] = Field(default_factory=list)
    passages: list[WikiPassageHitOut] = Field(default_factory=list)


# ── 支付 ──
class CreateOrderIn(CamelModel):
    kind: Literal["lamp", "merit"]
    plan: str | None = None
    amount_fen: int | None = None
    ref_id: str | None = None

    @field_validator("plan")
    @classmethod
    def _plan(cls, v: str | None) -> str | None:
        if v is not None and v not in LAMP_PLANS:
            raise ValueError("未知的供灯档位")
        return v

    def validate_semantics(self) -> None:
        if self.kind == "lamp":
            if self.plan is None:
                raise ValueError("供灯需指定档位")
        else:  # merit
            if self.amount_fen is None:
                raise ValueError("随喜需指定金额")
            if not (MERIT_MIN_FEN <= self.amount_fen <= MERIT_MAX_FEN):
                raise ValueError(f"随喜金额需在 {MERIT_MIN_FEN}~{MERIT_MAX_FEN} 分之间")


class OrderOut(CamelModel):
    order_id: str
    out_trade_no: str
    amount_fen: int
    status: Literal["pending", "paid", "failed", "refunded"]
    pay_params: dict | None
