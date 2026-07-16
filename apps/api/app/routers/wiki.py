from __future__ import annotations

from fastapi import APIRouter, Query

from app.core.errors import not_found
from app.schemas import (
    WikiConceptDetailOut,
    WikiDomainDetailOut,
    WikiDomainSummaryOut,
    WikiEvidencePageOut,
    WikiSearchOut,
)
from app.services import wiki

router = APIRouter(prefix="/api/wiki", tags=["wiki"])


@router.get("/domains", response_model=list[WikiDomainSummaryOut])
async def domains() -> list[WikiDomainSummaryOut]:
    return [WikiDomainSummaryOut.model_validate(d) for d in wiki.list_domains()]


@router.get("/domains/{slug}", response_model=WikiDomainDetailOut)
async def domain(slug: str) -> WikiDomainDetailOut:
    detail = wiki.domain_detail(slug)
    if detail is None:
        raise not_found("知识领域不存在")
    return WikiDomainDetailOut.model_validate(detail)


@router.get("/concepts/{concept_id}", response_model=WikiConceptDetailOut)
async def concept(concept_id: str) -> WikiConceptDetailOut:
    detail = wiki.concept_detail(concept_id)
    if detail is None:
        raise not_found("概念词条不存在")
    return WikiConceptDetailOut.model_validate(detail)


@router.get("/concepts/{concept_id}/evidence", response_model=WikiEvidencePageOut)
async def concept_evidence(
    concept_id: str,
    q: str = Query(default="", max_length=50),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=50),
) -> WikiEvidencePageOut:
    page = wiki.concept_evidence(concept_id, offset=offset, limit=limit, query=q)
    if page is None:
        raise not_found("概念词条不存在")
    return WikiEvidencePageOut.model_validate(page)


@router.get("/search", response_model=WikiSearchOut)
async def search(
    q: str = Query(min_length=1, max_length=50),
    limit: int = Query(default=8, ge=1, le=20),
) -> WikiSearchOut:
    return WikiSearchOut.model_validate(wiki.search(q, limit))
