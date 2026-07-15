"""认证：手机号登录，以及免手机号产品端使用的匿名访客会话。"""

from __future__ import annotations

import secrets

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import bad_request, rate_limited, service_unavailable
from app.core.redis_client import get_kv
from app.core.security import create_token
from app.models import User
from app.providers.sms import SmsDeliveryError, get_sms
from app.schemas import AuthOut, UserOut
from app.services.quota import is_lamp_user

CODE_TTL = 300  # 验证码 5 分钟有效
SEND_COOLDOWN = 60  # 同号 60 秒只能发一次
SEND_DAILY_CAP = 10  # 同号每日发码上限


def _code_key(phone: str) -> str:
    return f"sms:code:{phone}"


def _cooldown_key(phone: str) -> str:
    return f"sms:cd:{phone}"


def _daily_key(phone: str) -> str:
    return f"sms:daily:{phone}"


async def send_code(phone: str) -> str | None:
    kv = await get_kv()

    cooldown_key = _cooldown_key(phone)
    daily_key = _daily_key(phone)
    if not await kv.set_if_absent(cooldown_key, "1", SEND_COOLDOWN):
        raise rate_limited("验证码已发送，请 60 秒后再试")

    daily = await kv.incr_with_ttl(daily_key, 86400)
    if daily > SEND_DAILY_CAP:
        await kv.delete(cooldown_key)
        await kv.decrement(daily_key)
        raise rate_limited("今日验证码发送次数已达上限")

    code = f"{secrets.randbelow(1_000_000):06d}"
    try:
        await get_sms().send_code(phone, code)
    except (SmsDeliveryError, RuntimeError) as exc:
        await kv.delete(cooldown_key)
        await kv.decrement(daily_key)
        message = str(exc) if isinstance(exc, SmsDeliveryError) else "短信服务暂时不可用，请稍后重试"
        raise service_unavailable(message) from exc
    await kv.set(_code_key(phone), code, CODE_TTL)
    # 本地 console provider 不会发真实短信；仅在 development 返回验证码，
    # 方便本地联调，生产环境永远不把验证码放进 HTTP 响应。
    return code if settings.is_dev and settings.sms_provider == "console" else None


async def login(db: AsyncSession, phone: str, code: str) -> AuthOut:
    kv = await get_kv()
    saved = await kv.get(_code_key(phone))
    if not saved:
        raise bad_request("验证码已过期，请重新获取")
    if saved != code:
        raise bad_request("验证码错误")
    await kv.delete(_code_key(phone))

    user = await db.scalar(select(User).where(User.phone == phone))
    if user is None:
        user = User(phone=phone)
        db.add(user)
        await db.commit()
        await db.refresh(user)

    token = create_token(user.id)
    lamp = await is_lamp_user(db, user.id)
    return AuthOut(
        token=token,
        user=UserOut(id=user.id, phone=user.phone, nickname=user.nickname, is_lamp=lamp),
    )


async def create_guest(db: AsyncSession) -> AuthOut:
    """创建无需手机号的匿名访客。

    访客仍然拥有服务端用户记录，因此摇签配额、香火计时、愿望、问卦历史
    与命盘都保持服务端权威。内部占位标识不会在桌面产品界面中展示。
    """
    phone = f"guest_{secrets.token_hex(7)}"
    user = User(phone=phone, nickname="山中访客")
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return AuthOut(
        token=create_token(user.id),
        user=UserOut(id=user.id, phone=user.phone, nickname=user.nickname, is_lamp=False),
    )
