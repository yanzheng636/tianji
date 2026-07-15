from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import get_current_user, get_optional_user
from app.models import User
from app.schemas import CreateWishIn, WishOut, WishPoolOut
from app.services import wish

router = APIRouter(prefix="/api/wishes", tags=["wishes"])


@router.get("", response_model=WishPoolOut)
async def pool(
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
) -> WishPoolOut:
    return await wish.pool(db, user.id if user else None)


@router.post("", response_model=WishOut)
async def create(
    body: CreateWishIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WishOut:
    return await wish.create(db, user.id, body.text)


@router.post("/{wish_id}/fulfill", response_model=WishOut)
async def fulfill(
    wish_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WishOut:
    return await wish.fulfill(db, user.id, wish_id)
