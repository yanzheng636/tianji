from __future__ import annotations

import json
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.errors import not_found
from app.core.security import get_current_user
from app.models import User
from app.schemas import DrawQianIn, QianOut, QuotaOut, SavedStateOut, SaveQianIn
from app.services import qian
from app.services.quota import get_quota

router = APIRouter(prefix="/api/qian", tags=["qian"])


@router.post("/draw", response_model=QianOut)
async def draw(
    body: DrawQianIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QianOut:
    return await qian.draw(db, user.id, body.hall, body.topic)


@router.get("/quota", response_model=QuotaOut)
async def quota(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> QuotaOut:
    return await get_quota(db, user.id, "qian")


@router.get("/saved", response_model=list[QianOut])
async def saved_qians(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[QianOut]:
    return await qian.list_saved(db, user.id)


@router.post("/{draw_id}/save", response_model=SavedStateOut)
async def save_qian(
    draw_id: str,
    body: SaveQianIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SavedStateOut:
    saved = await qian.set_saved(db, user.id, draw_id, body.saved)
    if saved is None:
        raise not_found("这支签不存在")
    return SavedStateOut(saved=saved)


def _sse(event: dict) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


@router.get("/{draw_id}/reading")
async def reading(
    draw_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    if await qian.get_by_draw_id(db, user.id, draw_id) is None:
        raise not_found("这支签不存在")

    async def gen() -> AsyncGenerator[str, None]:
        async for event in qian.interpret(db, user.id, draw_id):
            yield _sse(event)

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
