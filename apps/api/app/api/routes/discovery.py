from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from app.core.cache import cache_get, cache_set
from app.core.config import settings
from app.core.redis import get_redis
from app.services.discovery_apple import apple_feed
from app.services.discovery_genres import CURATED
from app.services.discovery_lb import similar_artists
from app.services.discovery_mb import new_releases_by_genre

router = APIRouter(prefix="/api/v1/discovery", tags=["discovery"])
TTL = getattr(settings, "DISCOVERY_CACHE_TTL", 86_400)


@router.get("/genres")
def genres() -> dict[str, object]:
    return {"genres": CURATED}


@router.get("/new")
def new(
    genre: str,
    days: int = 30,
    limit: int = 50,
    redis=Depends(get_redis),
) -> dict[str, object]:
    cache_key = f"disc:new:{genre}:{days}:{limit}"
    cached = cache_get(redis, cache_key)
    if cached is not None:
        return cached
    try:
        items = new_releases_by_genre(genre, days, limit)
        payload = {"source": "musicbrainz", "items": items}
    except Exception as exc:  # pragma: no cover - converted into HTTP error
        raise HTTPException(status_code=502, detail=f"MusicBrainz error: {exc}") from exc
    cache_set(redis, cache_key, payload, TTL)
    return payload


@router.get("/top")
def top(
    genre_id: int,
    feed: str = "most-recent",
    kind: str = "albums",
    limit: int = 50,
    storefront: Optional[str] = None,
    redis=Depends(get_redis),
) -> dict[str, object]:
    storefront_code = storefront or getattr(settings, "APPLE_RSS_STOREFRONT", "us")
    cache_key = f"disc:top:{storefront_code}:{genre_id}:{feed}:{kind}:{limit}"
    cached = cache_get(redis, cache_key)
    if cached is not None:
        return cached
    try:
        items = apple_feed(storefront_code, genre_id, feed, kind, limit)
        payload = {"source": "apple", "items": items}
    except Exception as exc:  # pragma: no cover - converted into HTTP error
        raise HTTPException(status_code=502, detail=f"Apple RSS error: {exc}") from exc
    cache_set(redis, cache_key, payload, TTL)
    return payload


@router.get("/similar-artists")
def similar(
    artist_mbid: str,
    limit: int = 20,
    redis=Depends(get_redis),
) -> dict[str, object]:
    cache_key = f"disc:sim:{artist_mbid}:{limit}"
    cached = cache_get(redis, cache_key)
    if cached is not None:
        return cached
    try:
        items = similar_artists(artist_mbid, limit)
        payload = {"source": "listenbrainz", "items": items}
    except Exception as exc:  # pragma: no cover - converted into HTTP error
        raise HTTPException(status_code=502, detail=f"ListenBrainz error: {exc}") from exc
    cache_set(redis, cache_key, payload, TTL)
    return payload


__all__ = ["router"]
