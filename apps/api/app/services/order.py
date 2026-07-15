"""支付订单：下单 → 支付 → 幂等履约（发放供灯权益 / 记功德）。

- out_trade_no 唯一，作幂等键
- 履约只认「pending → paid」这一次跃迁，重复回调安全
- mock 下单后起后台任务几秒自动成功，跑通完整闭环
"""

from __future__ import annotations

import asyncio
import logging
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import LAMP_PLAN_META
from app.core.db import SessionLocal
from app.core.errors import not_found, payment_error
from app.models import Entitlement, Order
from app.providers.payment import get_payment
from app.schemas import CreateOrderIn, OrderOut

logger = logging.getLogger("tianji.order")


def _out_trade_no() -> str:
    ts = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    return f"TJ{ts}{secrets.token_hex(4)}"


def _to_out(row: Order, pay_params: dict | None = None) -> OrderOut:
    return OrderOut(
        order_id=row.id,
        out_trade_no=row.out_trade_no,
        amount_fen=row.amount_fen,
        status=row.status,  # type: ignore[arg-type]
        pay_params=pay_params,
    )


def _resolve_amount_subject(data: CreateOrderIn) -> tuple[int, str, str | None]:
    if data.kind == "lamp":
        meta = LAMP_PLAN_META[data.plan]  # type: ignore[index]
        return meta["price_fen"], f"供灯·{meta['name']}", data.plan
    # merit
    return int(data.amount_fen or 0), "随喜功德", None


async def create_order(db: AsyncSession, user_id: str, data: CreateOrderIn) -> OrderOut:
    data.validate_semantics()
    amount_fen, subject, plan = _resolve_amount_subject(data)

    provider = get_payment()
    out_trade_no = _out_trade_no()
    row = Order(
        user_id=user_id,
        out_trade_no=out_trade_no,
        kind=data.kind,
        plan=plan,
        amount_fen=amount_fen,
        status="pending",
        provider=provider.name,
        ref_id=data.ref_id,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)

    pay_params = await provider.create_payment(out_trade_no, amount_fen, subject)

    # mock：安排后台自动支付成功
    if provider.auto_confirm:
        asyncio.create_task(_auto_confirm(out_trade_no, delay=3.0))

    return _to_out(row, pay_params)


async def _auto_confirm(out_trade_no: str, delay: float) -> None:
    """mock 专用：延迟后用独立 session 履约。"""
    await asyncio.sleep(delay)
    try:
        async with SessionLocal() as db:
            await fulfill(db, out_trade_no, transaction_id=f"MOCK-{secrets.token_hex(6)}")
    except Exception:  # pragma: no cover
        logger.exception("mock 自动支付失败：%s", out_trade_no)


async def fulfill(db: AsyncSession, out_trade_no: str, transaction_id: str) -> None:
    """幂等履约：把订单置 paid 并发放权益。重复调用安全。"""
    row = await db.scalar(select(Order).where(Order.out_trade_no == out_trade_no))
    if row is None:
        raise not_found("订单不存在")
    if row.status == "paid":
        return  # 已履约，幂等返回

    row.status = "paid"
    row.transaction_id = transaction_id
    row.paid_at = datetime.now(UTC)

    # 履约：供灯 → 发放权益
    if row.kind == "lamp" and row.plan:
        meta = LAMP_PLAN_META[row.plan]
        now = datetime.now(UTC)
        expires = None if meta["days"] is None else now + timedelta(days=meta["days"])
        db.add(
            Entitlement(
                user_id=row.user_id,
                kind="lamp",
                plan=row.plan,
                starts_at=now,
                expires_at=expires,
                order_id=row.id,
            )
        )
    # merit（随喜）无额外权益，仅记账

    await db.commit()
    logger.info("订单履约完成：%s（%s）", out_trade_no, row.kind)


async def get_order(db: AsyncSession, user_id: str, order_id: str) -> OrderOut:
    row = await db.get(Order, order_id)
    if row is None or row.user_id != user_id:
        raise not_found("订单不存在")
    return _to_out(row)


async def handle_notify(headers: dict, raw_body: bytes) -> None:
    """真实支付平台回调入口。验签由 provider 负责，失败会抛异常。"""
    provider = get_payment()
    notify = await provider.parse_notify(headers, raw_body)
    if not notify.paid:
        raise payment_error("支付未成功")
    async with SessionLocal() as db:
        await fulfill(db, notify.out_trade_no, notify.transaction_id)
