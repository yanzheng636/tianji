from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import get_current_user
from app.models import User
from app.schemas import AuthOut, LoginIn, SendCodeIn, UserOut
from app.services import auth
from app.services.quota import is_lamp_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/send-code")
async def send_code(body: SendCodeIn) -> dict:
    dev_code = await auth.send_code(body.phone)
    return {"ok": True, **({"devCode": dev_code} if dev_code else {})}


@router.post("/login", response_model=AuthOut)
async def login(body: LoginIn, db: AsyncSession = Depends(get_db)) -> AuthOut:
    return await auth.login(db, body.phone, body.code)


@router.post("/guest", response_model=AuthOut)
async def guest(db: AsyncSession = Depends(get_db)) -> AuthOut:
    """为无需手机号认证的产品端建立匿名会话。"""
    return await auth.create_guest(db)


@router.get("/me", response_model=UserOut)
async def me(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> UserOut:
    lamp = await is_lamp_user(db, user.id)
    return UserOut(id=user.id, phone=user.phone, nickname=user.nickname, is_lamp=lamp)
