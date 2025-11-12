from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Query

from phelia.discovery.models import AlbumItem, ProvidersStatus
from phelia.discovery.service import (
    get_charts,
    get_new_releases,
    get_tag,
    providers_status,
    quick_search,
)

router = APIRouter()


@router.get("/charts", response_model=List[AlbumItem])
async def charts(
    market: Optional[str] = Query(default=None), limit: int = 50
) -> List[AlbumItem]:
    return await get_charts(market=market, limit=limit)


@router.get("/tags", response_model=List[AlbumItem])
async def tags(tag: str, limit: int = 50) -> List[AlbumItem]:
    return await get_tag(tag=tag, limit=limit)


@router.get("/new", response_model=List[AlbumItem])
async def new(
    market: Optional[str] = Query(default=None), limit: int = 50
) -> List[AlbumItem]:
    return await get_new_releases(market=market, limit=limit)


@router.get("/search", response_model=List[AlbumItem])
async def search(q: str, limit: int = 25) -> List[AlbumItem]:
    return await quick_search(query=q, limit=limit)


@router.get("/providers/status", response_model=ProvidersStatus)
async def status() -> ProvidersStatus:
    return await providers_status()
