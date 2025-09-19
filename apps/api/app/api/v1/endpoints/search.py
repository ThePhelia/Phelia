"""Search endpoint returning classified + enriched Jackett results."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from app.services.jackett_adapter import JackettAdapter


router = APIRouter(prefix="/search", tags=["metadata-search"])


def get_adapter() -> JackettAdapter:
    return JackettAdapter()


@router.get("")
async def search(
    q: str = Query(..., min_length=2, alias="q"),
    limit: int = Query(40, ge=1, le=100),
    adapter: JackettAdapter = Depends(get_adapter),
) -> dict[str, Any]:
    cards, meta = await adapter.search_with_metadata(q, limit=limit)
    payload: dict[str, Any] = {"items": [card.model_dump() for card in cards]}
    payload.update(meta)
    return payload

