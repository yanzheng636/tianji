from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.errors import not_found
from app.schemas import BookDetailOut, BookSummaryOut, CitationOut
from app.services import scripture

router = APIRouter(prefix="/api/scripture", tags=["scripture"])


@router.get("/books", response_model=list[BookSummaryOut])
async def books(db: AsyncSession = Depends(get_db)) -> list[BookSummaryOut]:
    return await scripture.list_books(db)


@router.get("/books/{slug}", response_model=BookDetailOut)
async def book(slug: str, db: AsyncSession = Depends(get_db)) -> BookDetailOut:
    b = await scripture.get_book(db, slug)
    if b is None:
        raise not_found("经卷不存在")
    return b


@router.get("/search", response_model=list[CitationOut])
async def search(
    q: str = Query(min_length=1, max_length=50),
    limit: int = Query(default=5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
) -> list[CitationOut]:
    return await scripture.search(db, q, limit)
