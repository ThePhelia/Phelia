"""Discovery routes bridging optional providers with FastAPI."""

from __future__ import annotations

import json
from collections.abc import Callable, Generator, Iterable, Sequence
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.config import settings

apple_feed = None  # type: ignore[assignment]
new_releases_by_genre = None  # type: ignore[assignment]
similar_artists = None  # type: ignore[assignment]
discovery_service = None  # type: ignore[assignment]
DEFAULT_PROVIDER_STATUS = {
    "lastfm": False,
    "deezer": False,
    "itunes": False,
    "musicbrainz": False,
    "listenbrainz": False,
    "spotify": False,
}

try:  # pragma: no cover - optional providers might not be available in tests
    from app.services.discovery_apple import apple_feed as _apple_feed
except Exception:  # pragma: no cover - importer resilience
    _apple_feed = None
else:
    apple_feed = _apple_feed

try:  # pragma: no cover - optional providers might not be available in tests
    from app.services.discovery_mb import new_releases_by_genre as _new_releases_by_genre
except Exception:  # pragma: no cover - importer resilience
    _new_releases_by_genre = None
else:
    new_releases_by_genre = _new_releases_by_genre

try:  # pragma: no cover - optional providers might not be available in tests
    from app.services.discovery_lb import similar_artists as _similar_artists
except Exception:  # pragma: no cover - importer resilience
    _similar_artists = None
else:
    similar_artists = _similar_artists

try:  # pragma: no cover - optional providers might not be available in tests
    from phelia.discovery import service as _phelia_discovery_service
except Exception:  # pragma: no cover - importer resilience
    _phelia_discovery_service = None
else:

    def _model_dump(item: Any) -> Dict[str, Any]:  # pragma: no cover - thin adapter
        if hasattr(item, "model_dump"):
            return item.model_dump(mode="json")  # type: ignore[no-any-return]
        if isinstance(item, dict):
            return dict(item)
        data = {}
        for key in ("id", "title", "artist", "cover_url", "release_date", "source", "tags"):
            value = getattr(item, key, None)
            if value is not None:
                data[key] = value
        return data

    class _DiscoveryServiceAdapter:  # pragma: no cover - behaviour exercised via routes
        def __init__(self, module: Any) -> None:
            self._module = module

        async def fetch_new_albums(self, tag: str, since: str, limit: int) -> list[dict[str, Any]]:  # noqa: ARG002 - since unused
            items = await self._module.get_tag(tag=tag, limit=limit)
            return [_model_dump(item) for item in items]

        async def fetch_top(self, *, kind: str, tag: str, feed: str, limit: int) -> list[dict[str, Any]]:  # noqa: ARG002 - unused params
            items = await self._module.get_tag(tag=tag, limit=limit)
            return [_model_dump(item) for item in items]

        async def search(self, query: str, limit: int) -> list[dict[str, Any]]:
            items = await self._module.quick_search(query=query, limit=limit)
            return [_model_dump(item) for item in items]

        async def providers_status(self) -> dict[str, bool]:
            status = await self._module.providers_status()
            if hasattr(status, "model_dump"):
                return status.model_dump()
            if isinstance(status, dict):
                return status
            return DEFAULT_PROVIDER_STATUS.copy()

    discovery_service = _DiscoveryServiceAdapter(_phelia_discovery_service)
#
# If your module previously imported/defined `discovery_service` and `GENRES_BY_ID`,
# keep them present. This file is resilient: it will use them when available,
# and gracefully fall back to MusicBrainz/CAA when not.
#

router = APIRouter(prefix="/api/v1/discovery", tags=["discovery"])


def get_redis():  # pragma: no cover - default dependency for overrides
    return None


def _resolve_cache_backend(candidate: Any) -> Any:
    """Normalize redis dependency outputs (generator, direct client, None)."""

    if candidate in (None, False):
        return None

    if isinstance(candidate, Generator):
        try:
            value = next(candidate)
        except StopIteration:
            return None
        try:  # pragma: no cover - defensive cleanup
            candidate.close()
        except Exception:
            pass
        return value

    return candidate


def _get_cache(redis: Any) -> Any:
    cache = _resolve_cache_backend(redis)
    if cache not in (None, False):
        return cache

    fallback: Callable[[], Any] | None = globals().get("get_redis")  # type: ignore[assignment]
    if callable(fallback):
        try:
            cache = _resolve_cache_backend(fallback())
        except TypeError:
            cache = _resolve_cache_backend(fallback)  # pragma: no cover - defensive branch
        if cache not in (None, False):
            return cache

    return None


def _extract_items_from_payload(data: Any) -> list[Any]:
    if not data:
        return []
    if isinstance(data, dict):
        items = data.get("items")
        if isinstance(items, list):
            return items
        return []
    if isinstance(data, list):
        return data
    return []


def _normalize_items(items: Iterable[Any]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for item in items:
        if not item:
            continue
        if hasattr(item, "model_dump"):
            data = item.model_dump(mode="json")  # type: ignore[assignment]
        elif isinstance(item, dict):
            data = dict(item)
        else:
            data = {}
            for key in (
                "id",
                "title",
                "artist",
                "cover_url",
                "cover",
                "artwork",
                "release_date",
                "releaseDate",
                "source",
                "source_url",
                "url",
            ):
                value = getattr(item, key, None)
                if value is not None:
                    data[key] = value
        if "title" not in data and "name" in data:
            data["title"] = data.get("name")
        if "artist" not in data and "artistName" in data:
            data["artist"] = data.get("artistName")
        if "artist" not in data and "creator" in data:
            data["artist"] = data.get("creator")
        normalized.append(data)
    return normalized


def _iter_items(data: Any) -> Iterable[Any]:
    items = _extract_items_from_payload(data)
    if items:
        return items
    if isinstance(data, dict):
        return [data]
    if isinstance(data, (str, bytes)):
        return []
    if isinstance(data, Iterable):
        return data
    return []


def _dedupe_items(items: Sequence[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for item in items:
        title = str(item.get("title", "")).strip().lower()
        artist = str(item.get("artist", "")).strip().lower()
        identifier = str(item.get("id") or "").strip()
        key = "::".join(filter(None, (identifier, title, artist)))
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(item)
        if len(out) >= limit:
            break
    return out


def _coerce_fields(item: dict[str, Any]) -> None:
    if "cover_url" not in item:
        for key in ("cover", "artwork", "artworkUrl100", "image"):
            value = item.get(key)
            if isinstance(value, str) and value:
                item["cover_url"] = value
                break
    if "release_date" not in item:
        for key in ("releaseDate", "firstReleaseDate", "first-release-date", "year"):
            value = item.get(key)
            if isinstance(value, str) and value:
                item["release_date"] = value
                break
    if "source" not in item:
        for key in ("provider", "origin", "storefront"):
            value = item.get(key)
            if isinstance(value, str) and value:
                item["source"] = value
                break


def _prepare_payload(items: Iterable[dict[str, Any]], limit: int) -> dict[str, Any]:
    normalized = _normalize_items(items)
    for entry in normalized:
        _coerce_fields(entry)
    deduped = _dedupe_items(normalized, limit)
    return {"items": deduped}


# Slug -> MusicBrainz tag normalization for common genres.
# Extend freely; keys are slugs you use in the UI.
GENRE_SLUG_TO_MB_TAG: Dict[str, str] = {
    "techno": "techno",
    "house": "house",
    "ambient": "ambient",
    "drum-and-bass": "drum and bass",
    "dnb": "drum and bass",
    "metal": "metal",
    "rock": "rock",
    "hip-hop": "hip hop",
    "hiphop": "hip hop",
    "electronic": "electronic",
    "indie": "indie",
    "pop": "pop",
    "jazz": "jazz",
    "classical": "classical",
}

def _safe_get_mb_tag_from_id(genre_id: Optional[int]) -> Optional[str]:
    """Resolve a MusicBrainz tag from internal GENRES_BY_ID mapping if it exists."""
    if genre_id is None:
        return None
    mapping = globals().get("GENRES_BY_ID")
    if not mapping:
        return None
    # mapping may be a dict with int or str keys. Values can be objects or dicts.
    rec = mapping.get(genre_id) or mapping.get(str(genre_id))
    if not rec:
        return None
    # Try object attribute first, then dict.
    mb_tag = getattr(rec, "musicbrainz_tag", None)
    if not mb_tag and isinstance(rec, dict):
        mb_tag = rec.get("musicbrainz_tag")
    return mb_tag

def _normalize_genre(tag: Optional[str], genre_id: Optional[int]) -> str:
    """Normalize input (?genre=slug OR ?genre_id=INT) into a MusicBrainz tag."""
    mb_tag = _safe_get_mb_tag_from_id(genre_id)
    if mb_tag:
        return mb_tag
    if tag:
        t = GENRE_SLUG_TO_MB_TAG.get(tag.strip().lower())
        if t:
            return t
    raise HTTPException(status_code=400, detail="Unknown genre/genre_id")

async def _mb_get_json(url: str, params: Dict[str, Any]) -> Dict[str, Any]:
    headers = {"User-Agent": "Phelia/1.0 (self-hosted)"}
    async with httpx.AsyncClient(timeout=15.0, headers=headers) as cx:
        try:
            r = await cx.get(url, params=params)
            r.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code if exc.response else 502
            detail = f"musicbrainz_error_{status_code}"
            raise HTTPException(status_code=status_code, detail=detail) from exc
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail="musicbrainz_unreachable") from exc
        return r.json()

@router.get("/genres")
async def list_genres():
    """Return your curated/static genres list (kept as-is if previously implemented)."""
    # If your project has a function like discovery_service.list_genres(), use it.
    svc = globals().get("discovery_service")
    if svc and hasattr(svc, "list_genres"):
        try:
            items = await svc.list_genres()  # type: ignore[func-returns-value]
            if items is not None:
                return items
        except Exception:
            pass
    # Minimal fallback. Replace with your actual static list if you have one.
    return [{"slug": k, "name": k.replace('-', ' ').title()} for k in sorted(GENRE_SLUG_TO_MB_TAG)]


@router.get("/providers/status")
async def providers_status(redis=Depends(get_redis)) -> dict[str, bool]:
    cache_key = "discovery:providers:status"
    cache = _get_cache(redis)
    if cache:
        cached = cache.get(cache_key)
        if cached:
            try:
                data = json.loads(cached)
                if isinstance(data, dict):
                    return {**DEFAULT_PROVIDER_STATUS, **data}
            except (TypeError, ValueError):
                pass

    payload = DEFAULT_PROVIDER_STATUS.copy()
    svc = globals().get("discovery_service")
    if svc and hasattr(svc, "providers_status"):
        try:
            status = await svc.providers_status()  # type: ignore[func-returns-value]
            if isinstance(status, dict):
                payload.update({k: bool(v) for k, v in status.items()})
        except Exception:
            pass

    if cache:
        cache.set(cache_key, json.dumps(payload), ex=300)
    return payload

@router.get("/new")
async def new_albums(
    genre_id: Optional[int] = Query(None, description="Internal genre id"),
    genre: Optional[str] = Query(None, description="Genre slug, e.g., 'techno'"),
    days: int = Query(30, ge=1, le=120),
    limit: int = Query(24, ge=1, le=100),
    redis = Depends(get_redis),
) -> dict[str, Any]:
    """Newly released albums for a given genre (keyless fallback supported)."""
    mb_tag = _normalize_genre(genre, genre_id)
    since = (datetime.utcnow() - timedelta(days=days)).date().isoformat()

    cache_key = f"discovery:new:{mb_tag}:{days}:{limit}"
    cache = _get_cache(redis)
    if cache:
        cached = cache.get(cache_key)
        if cached:
            try:
                return json.loads(cached)
            except (TypeError, ValueError):
                pass

    aggregate: list[dict[str, Any]] = []

    # Try existing provider first if discovery_service is available.
    svc = globals().get("discovery_service")
    if svc and hasattr(svc, "fetch_new_albums"):
        try:
            releases = await svc.fetch_new_albums(mb_tag, since, limit)  # type: ignore[arg-type]
            aggregate.extend(_normalize_items(_iter_items(releases)))
        except Exception:
            # fall through to other providers if adapter errors out
            pass

    provider_fn = globals().get("new_releases_by_genre")
    if callable(provider_fn):
        try:
            releases = provider_fn(mb_tag, days, limit)
            aggregate.extend(_normalize_items(_iter_items(releases)))
        except Exception as exc:  # pragma: no cover - provider specific
            raise HTTPException(status_code=502, detail=f"New releases provider error: {exc}")

    # MusicBrainz fallback (no keys required)
    if not aggregate:
        query = f'tag:"{mb_tag}" AND primarytype:Album AND firstreleasedate:[{since} TO *]'
        data = await _mb_get_json(
            "https://musicbrainz.org/ws/2/release-group",
            {"query": query, "fmt": "json", "limit": str(limit), "offset": "0"},
        )
        for rg in data.get("release-groups", []):
            aggregate.append(
                {
                    "id": rg.get("id"),
                    "title": rg.get("title"),
                    "artist": (rg.get("artist-credit") or [{}])[0].get("name"),
                    "releaseDate": rg.get("first-release-date"),
                    "cover": f"https://coverartarchive.org/release-group/{rg.get('id')}/front-250",
                    "source": "musicbrainz",
                }
            )

    payload = _prepare_payload(aggregate, limit)
    if cache:
        cache.set(cache_key, json.dumps(payload), ex=3600)
    return payload

@router.get("/top")
async def top_albums(
    genre_id: Optional[int] = Query(None),
    genre: Optional[str] = Query(None),
    kind: str = Query("albums", pattern="^(albums|artists)$"),
    feed: str = Query("most-recent", pattern="^(most-recent|weekly|monthly)$"),
    limit: int = Query(24, ge=1, le=100),
    redis = Depends(get_redis),
) -> dict[str, Any]:
    """Top albums (or artists) for a given genre; provider first, MB fallback next."""
    cache_subject = None
    if isinstance(genre, str) and genre.strip():
        cache_subject = f"slug:{genre.strip().lower()}"
    elif genre_id is not None:
        cache_subject = f"id:{genre_id}"
    else:
        cache_subject = "all"

    cache_key = f"discovery:top:{cache_subject}:{kind}:{feed}:{limit}"
    cache = _get_cache(redis)
    if cache:
        cached = cache.get(cache_key)
        if cached:
            try:
                return json.loads(cached)
            except (TypeError, ValueError):
                pass

    mb_tag: Optional[str] = None

    def ensure_mb_tag() -> Optional[str]:
        nonlocal mb_tag
        if mb_tag is not None:
            return mb_tag
        try:
            mb_tag = _normalize_genre(genre, genre_id)
        except HTTPException:
            mb_tag = None
        return mb_tag

    aggregate: list[dict[str, Any]] = []

    # Try existing provider first
    svc = globals().get("discovery_service")
    tag = ensure_mb_tag()
    if svc and hasattr(svc, "fetch_top") and tag:
        try:
            items = await svc.fetch_top(kind=kind, tag=tag, feed=feed, limit=limit)  # type: ignore[arg-type]
            aggregate.extend(_normalize_items(_iter_items(items)))
        except Exception:
            # continue to other providers on error
            pass

    apple_fn = globals().get("apple_feed")
    if callable(apple_fn):
        try:
            storefront = getattr(settings, "APPLE_RSS_STOREFRONT", "us")
            genre_key = genre_id if genre_id is not None else 0
            items = apple_fn(storefront, genre_key, feed, kind, limit)
            aggregate.extend(_normalize_items(_iter_items(items or [])))
        except httpx.HTTPError:
            pass
        except Exception as exc:  # pragma: no cover - provider specific
            raise HTTPException(status_code=502, detail=f"Apple RSS error: {exc}")

    # MusicBrainz fallback: get artists by tag, then latest album for each
    if not tag and not aggregate:
        raise HTTPException(status_code=400, detail="Unknown genre/genre_id")

    if not aggregate and tag:
        ar = await _mb_get_json(
            "https://musicbrainz.org/ws/2/artist",
            {"query": f'tag:"{tag}"', "fmt": "json", "limit": str(min(50, max(10, limit * 2)))},
        )
        for a in ar.get("artists", []):
            rg = await _mb_get_json(
                "https://musicbrainz.org/ws/2/release-group",
                {"query": f'artist:{a.get("id")} AND primarytype:Album', "fmt": "json", "limit": "1"},
            )
            rj = rg.get("release-groups", [])
            if not rj:
                continue
            rg0 = rj[0]
            aggregate.append(
                {
                    "id": rg0.get("id"),
                    "title": rg0.get("title"),
                    "artist": a.get("name"),
                    "releaseDate": rg0.get("first-release-date"),
                    "cover": f'https://coverartarchive.org/release-group/{rg0.get("id")}/front-250',
                    "source": "musicbrainz",
                }
            )
            if len(aggregate) >= limit:
                break

    payload = _prepare_payload(aggregate, limit)
    if cache:
        cache.set(cache_key, json.dumps(payload), ex=3600)
    return payload


@router.get("/search")
async def search_albums(
    q: str = Query(..., min_length=1),
    limit: int = Query(25, ge=1, le=100),
    redis=Depends(get_redis),
) -> dict[str, Any]:
    query = q.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Empty search query")

    cache_key = f"discovery:search:{query.lower()}:{limit}"
    cache = _get_cache(redis)
    if cache:
        cached = cache.get(cache_key)
        if cached:
            try:
                return json.loads(cached)
            except (TypeError, ValueError):
                pass

    aggregate: list[dict[str, Any]] = []
    svc = globals().get("discovery_service")
    if svc and hasattr(svc, "search"):
        try:
            items = await svc.search(query, limit)  # type: ignore[arg-type]
            aggregate.extend(_normalize_items(_iter_items(items)))
        except Exception:
            pass

    if len(aggregate) < limit:
        data = await _mb_get_json(
            "https://musicbrainz.org/ws/2/release-group",
            {"query": query, "fmt": "json", "limit": str(limit)},
        )
        for rg in data.get("release-groups", []):
            aggregate.append(
                {
                    "id": rg.get("id"),
                    "title": rg.get("title"),
                    "artist": (rg.get("artist-credit") or [{}])[0].get("name"),
                    "releaseDate": rg.get("first-release-date"),
                    "cover": f"https://coverartarchive.org/release-group/{rg.get('id')}/front-250",
                    "source": "musicbrainz",
                }
            )
            if len(aggregate) >= limit:
                break

    payload = _prepare_payload(aggregate, limit)
    if cache:
        cache.set(cache_key, json.dumps(payload), ex=900)
    return payload


@router.get("/similar-artists")
async def similar_artists_endpoint(
    artist_mbid: str = Query(..., description="MusicBrainz artist id"),
    limit: int = Query(10, ge=1, le=50),
    redis=Depends(get_redis),
) -> dict[str, Any]:
    """Return similar artists using the configured provider when available."""

    cache_key = f"discovery:similar:{artist_mbid}:{limit}"
    cache = _get_cache(redis)
    if cache:
        cached = cache.get(cache_key)
        if cached:
            try:
                return json.loads(cached)
            except (TypeError, ValueError):
                pass

    provider_fn = globals().get("similar_artists")
    if callable(provider_fn):
        try:
            items = provider_fn(artist_mbid, limit)
        except Exception as exc:  # pragma: no cover - provider specific
            raise HTTPException(status_code=502, detail=f"Similar artists provider error: {exc}")
        payload = {"items": items or []}
        if cache:
            cache.set(cache_key, json.dumps(payload), ex=3600)
        return payload

    raise HTTPException(status_code=404, detail="similar_artist_provider_unavailable")
