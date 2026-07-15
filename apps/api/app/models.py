"""SQLAlchemy 2.0 ORM 模型。

设计原则：
 - 金额一律 Int（分）
 - 一切「命运结果」（签、上香计时）由服务端产生并落库，前端不可篡改
 - UGC（许愿）带审核状态
 - 支付订单幂等 + 状态机
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


def _cuid() -> str:
    # 轻量唯一 id：时间戳 + 随机。无需额外依赖。
    import secrets

    return secrets.token_hex(12)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_cuid)
    phone: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    nickname: Mapped[str | None] = mapped_column(String(40))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    profile: Mapped[BirthProfile | None] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )


class BirthProfile(Base, TimestampMixin):
    """出生信息（八字排盘输入）。掌纹等生物识别信息不落库。"""

    __tablename__ = "birth_profiles"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_cuid)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )
    gender: Mapped[str] = mapped_column(String(10))  # male | female
    birth_date: Mapped[str] = mapped_column(String(10))  # YYYY-MM-DD 公历
    birth_hour: Mapped[int | None] = mapped_column(Integer)  # 0-23，未知为 null
    birth_place: Mapped[str | None] = mapped_column(String(60))
    chart_json: Mapped[dict | None] = mapped_column(JSONB)  # 排盘缓存
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[User] = relationship(back_populates="profile")


class QianDraw(Base, TimestampMixin):
    """摇签记录（服务端发签，杜绝前端重摇）。"""

    __tablename__ = "qian_draws"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_cuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    hall: Mapped[str] = mapped_column(String(20))
    topic: Mapped[str] = mapped_column(String(20))
    qian_slug: Mapped[str] = mapped_column(String(40))

    __table_args__ = (Index("ix_qian_user_created", "user_id", "created_at"),)


class IncenseSession(Base, TimestampMixin):
    """上香（服务端权威计时）。"""

    __tablename__ = "incense_sessions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_cuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    type: Mapped[str] = mapped_column(String(10))
    wish_id: Mapped[str | None] = mapped_column(String(32))
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    duration_sec: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(12), default="burning")  # burning|done|cancelled

    __table_args__ = (Index("ix_incense_user_status", "user_id", "status"),)


class Wish(Base, TimestampMixin):
    """许愿池（UGC，带审核）。"""

    __tablename__ = "wishes"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_cuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    text: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(12), default="active")  # active|fulfilled
    moderation: Mapped[str] = mapped_column(
        String(12), default="pending"
    )  # pending|approved|rejected
    moderation_reason: Mapped[str | None] = mapped_column(String(100))
    fulfilled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("ix_wish_moderation_created", "moderation", "created_at"),
        Index("ix_wish_user_created", "user_id", "created_at"),
    )


class ChatMessage(Base, TimestampMixin):
    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_cuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String(12))  # user | assistant
    text: Mapped[str] = mapped_column(Text)
    citation_json: Mapped[dict | None] = mapped_column(JSONB)

    __table_args__ = (Index("ix_chat_user_created", "user_id", "created_at"),)


class Book(Base):
    __tablename__ = "books"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_cuid)
    slug: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    char: Mapped[str] = mapped_column(String(4))
    name: Mapped[str] = mapped_column(String(40))
    meta: Mapped[str] = mapped_column(String(80))
    sort: Mapped[int] = mapped_column(Integer, default=0)

    passages: Mapped[list[Passage]] = relationship(
        back_populates="book", cascade="all, delete-orphan"
    )


class Passage(Base):
    __tablename__ = "passages"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_cuid)
    book_id: Mapped[str] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"))
    chapter: Mapped[str] = mapped_column(String(60))
    text: Mapped[str] = mapped_column(Text)
    plain: Mapped[str] = mapped_column(Text, default="")
    topic: Mapped[str] = mapped_column(String(20), default="general")
    # 关键词检索加权用的术语标签
    tags: Mapped[list[str] | None] = mapped_column(JSONB)
    embedding: Mapped[list[float] | None] = mapped_column(JSONB)  # 无 pgvector 时存 JSON
    sort: Mapped[int] = mapped_column(Integer, default=0)

    book: Mapped[Book] = relationship(back_populates="passages")

    __table_args__ = (Index("ix_passage_book_sort", "book_id", "sort"),)


class Order(Base, TimestampMixin):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_cuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    out_trade_no: Mapped[str] = mapped_column(String(40), unique=True, index=True)  # 幂等键
    kind: Mapped[str] = mapped_column(String(12))  # lamp | merit
    plan: Mapped[str | None] = mapped_column(String(12))
    amount_fen: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(
        String(12), default="pending"
    )  # pending|paid|failed|refunded
    provider: Mapped[str] = mapped_column(String(12))
    transaction_id: Mapped[str | None] = mapped_column(String(64))
    ref_id: Mapped[str | None] = mapped_column(String(32))
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("ix_order_user_created", "user_id", "created_at"),
        Index("ix_order_status", "status"),
    )


class Entitlement(Base, TimestampMixin):
    """已购权益（供灯期限）。paid 订单履约后写入。"""

    __tablename__ = "entitlements"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_cuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(String(12))  # lamp
    plan: Mapped[str] = mapped_column(String(12))
    starts_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # null=永久
    order_id: Mapped[str | None] = mapped_column(String(32))

    __table_args__ = (Index("ix_entitlement_user_expires", "user_id", "expires_at"),)


class DailyQuota(Base):
    """每日额度（摇签/问卦限流）。"""

    __tablename__ = "daily_quota"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    day: Mapped[str] = mapped_column(String(10))  # YYYY-MM-DD
    kind: Mapped[str] = mapped_column(String(12))  # qian | chat
    used: Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (UniqueConstraint("user_id", "day", "kind", name="uq_quota"),)
