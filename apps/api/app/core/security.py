"""JWT 签发 / 校验 + 当前用户依赖。"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_db
from app.core.errors import unauthorized
from app.models import User

ALGORITHM = "HS256"


def create_token(user_id: str) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": user_id,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=settings.jwt_expires_days)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def _decode(token: str) -> str:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
        return str(payload["sub"])
    except jwt.PyJWTError as e:  # 过期 / 签名错 / 格式错
        raise unauthorized("登录已失效，请重新登录") from e


def _extract_token(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        raise unauthorized()
    return auth[7:].strip()


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    token = _extract_token(request)
    user_id = _decode(token)
    user = await db.scalar(select(User).where(User.id == user_id))
    if user is None:
        raise unauthorized("账号不存在")
    return user


async def get_optional_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """许愿池等接口：登录可看「我的」，未登录只看公共池。"""
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        return None
    try:
        user_id = _decode(auth[7:].strip())
    except Exception:
        return None
    return await db.scalar(select(User).where(User.id == user_id))
