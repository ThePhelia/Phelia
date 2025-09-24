from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.schemas.meta import JackettSearchItem, JackettSearchResponse, MetaItemType, StartIndexingPayload
from app.services.jackett_adapter import JackettAdapter
from app.services.jobs import tasks as jobs_tasks
from app.services.meta.canonical import build_from_payload

router = APIRouter(tags=["indexing"])
logger = logging.getLogger(__name__)

_DEFAULT_CATEGORIES: dict[MetaItemType, list[int]] = {
    "movie": [2000, 5000],
    "tv": [5000],
    "album": [3000],
}


def _parse_categories(raw: str | None) -> list[int] | None:
    if not raw:
        return None
    categories: list[int] = []
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            categories.append(int(chunk))
        except ValueError:  # pragma: no cover - defensive
            logger.debug("Skipping invalid Jackett category value: %s", chunk)
    return categories or None


def _categories_for_item(item_type: MetaItemType) -> list[int] | None:
    override = None
    if item_type == "movie":
        override = _parse_categories(getattr(settings, "JACKETT_MOVIE_CATS", None))
    elif item_type == "tv":
        override = _parse_categories(getattr(settings, "JACKETT_TV_CATS", None))
    elif item_type == "album":
        override = _parse_categories(getattr(settings, "JACKETT_MUSIC_CATS", None))
    if override is not None:
        return override
    return _DEFAULT_CATEGORIES.get(item_type)


@router.post("/start", response_model=JackettSearchResponse)
async def start_indexing(payload: StartIndexingPayload) -> JackettSearchResponse:
    canonical = build_from_payload(payload)
    query = canonical.query.strip()
    if not query:
        raise HTTPException(status_code=422, detail="empty_query")

    categories = _categories_for_item(payload.type)
    adapter = JackettAdapter()
    try:
        results = await adapter.search(query=query, categories=categories)
    except Exception as exc:
        logger.warning("jackett search failed query=%s error=%s", query, exc)
        raise HTTPException(status_code=502, detail="jackett_error") from exc

    try:
        jobs_tasks.index_with_jackett.delay({"query": query, "categories": categories, "type": payload.type})
    except Exception as exc:  # pragma: no cover - best-effort integration
        logger.debug("Celery dispatch for Jackett indexing failed: %s", exc)

    items = [JackettSearchItem(**item) for item in results]
    return JackettSearchResponse(query=query, results=items)
