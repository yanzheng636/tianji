from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import LAMP_PLAN_META, MERIT_PRESETS_FEN
from app.core.db import get_db
from app.core.security import get_current_user
from app.models import User
from app.schemas import CreateOrderIn, OrderOut
from app.services import order

router = APIRouter(prefix="/api/pay", tags=["payment"])


@router.get("/options")
async def options() -> dict:
    return {
        "lampPlans": list(LAMP_PLAN_META.values()),
        "meritPresetsFen": list(MERIT_PRESETS_FEN),
    }


@router.post("/orders", response_model=OrderOut)
async def create_order(
    body: CreateOrderIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrderOut:
    return await order.create_order(db, user.id, body)


@router.get("/orders/{order_id}", response_model=OrderOut)
async def get_order(
    order_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrderOut:
    return await order.get_order(db, user.id, order_id)


@router.post("/notify/{provider}")
async def notify(provider: str, request: Request) -> PlainTextResponse:
    """支付平台异步回调（真支付用）。mock 不走这里。"""
    raw = await request.body()
    await order.handle_notify(dict(request.headers), raw)
    # 微信/支付宝要求返回特定成功报文；这里给通用 200
    return PlainTextResponse("SUCCESS")
