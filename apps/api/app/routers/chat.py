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
from app.schemas import ChatIn, ChatMessageOut, ChatSessionOut
from app.services import chat

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.get("/history", response_model=list[ChatMessageOut])
async def history(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[ChatMessageOut]:
    return await chat.history(db, user.id)


@router.get("/sessions", response_model=list[ChatSessionOut])
async def sessions(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[ChatSessionOut]:
    return await chat.list_sessions(db, user.id)


@router.post("/sessions", response_model=ChatSessionOut)
async def new_session(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> ChatSessionOut:
    return await chat.create_session(db, user.id)


@router.get("/sessions/{session_id}/messages", response_model=list[ChatMessageOut])
async def session_messages(
    session_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ChatMessageOut]:
    return await chat.session_messages(db, user.id, session_id)


@router.delete("/sessions/{session_id}", status_code=204)
async def remove_session(
    session_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    if not await chat.delete_session(db, user.id, session_id):
        raise not_found("会话不存在")


def _sse(event: dict) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


@router.post("/stream")
async def stream(
    body: ChatIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    async def gen() -> AsyncGenerator[str, None]:
        async for event in chat.stream_reply(
            db, user.id, body.text, body.qian_id, body.session_id
        ):
            yield _sse(event)

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 关闭 nginx 缓冲，确保逐字流出
        },
    )
