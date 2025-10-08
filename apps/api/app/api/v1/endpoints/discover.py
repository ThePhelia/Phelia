"""Discovery endpoints that surface curated media suggestions."""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.config import settings
from app.schemas.discover import DiscoverItem, PaginatedResponse
from app.services.metadata.constants import TMDB_IMAGE_BASE
from app.services.metadata.metadata_client import MetadataProxyError, get_metadata_client
from app.services.metadata.providers.musicbrainz import MusicBrainzClient


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/discover", tags=["discover"])

SortOption = Literal["trending", "popular", "new", "az"]


@lru_cache
def _musicbrainz_client() -> MusicBrainzClient:
    return MusicBrainzClient(user_agent=settings.MB_USER_AGENT)


def get_musicbrainz_client() -> MusicBrainzClient:
    return _musicbrainz_client()


def _tmdb_discover_request(
    media_type: Literal["movie", "tv"], sort: SortOption, page: int
) -> tuple[str, dict[str, Any]]:
    normalized = (sort or "trending").lower()
    params: dict[str, Any] = {"page": max(1, page), "language": "en-US"}
    if normalized == "popular":
        path = f"{media_type}/popular"
    elif normalized == "new":
        path = "movie/now_playing" if media_type == "movie" else "tv/on_the_air"
    elif normalized == "az":
        path = f"discover/{media_type}"
        params.update({"sort_by": "original_title.asc", "include_adult": False})
    else:
        path = f"trending/{media_type}/day"
    return path, params


@router.get("/movie", response_model=PaginatedResponse[DiscoverItem])
async def discover_movies(
    sort: SortOption = Query("trending"),
    page: int = Query(1, ge=1, le=1000),
) -> PaginatedResponse[DiscoverItem]:
    metadata = get_metadata_client()
    return await _discover_video("movie", sort, page, metadata)


@router.get("/tv", response_model=PaginatedResponse[DiscoverItem])
async def discover_tv(
    sort: SortOption = Query("trending"),
    page: int = Query(1, ge=1, le=1000),
) -> PaginatedResponse[DiscoverItem]:
    metadata = get_metadata_client()
    return await _discover_video("tv", sort, page, metadata)


@router.get("/album", response_model=PaginatedResponse[DiscoverItem])
async def discover_albums(
    sort: SortOption = Query("trending"),
    page: int = Query(1, ge=1, le=1000),
    musicbrainz: MusicBrainzClient = Depends(get_musicbrainz_client),
) -> PaginatedResponse[DiscoverItem]:
    metadata = get_metadata_client()
    return await _discover_albums(sort, page, metadata, musicbrainz)


FALLBACK_PAYLOAD: dict[str, list[dict[str, Any]]] = {
    "movie": [
        {
            "kind": "movie",
            "id": "fallback:movie:blade-runner",
            "title": "Blade Runner",
            "subtitle": "Directed by Ridley Scott",
            "year": 1982,
            "genres": ["Science Fiction", "Thriller"],
            "badges": ["Classic"],
            "meta": {"source": "fallback"},
        },
        {
            "kind": "movie",
            "id": "fallback:movie:inception",
            "title": "Inception",
            "subtitle": "A mind-bending heist thriller",
            "year": 2010,
            "genres": ["Science Fiction", "Action"],
            "badges": ["Fan Favorite"],
            "meta": {"source": "fallback"},
        },
    ],
    "tv": [
        {
            "kind": "tv",
            "id": "fallback:tv:the-expanse",
            "title": "The Expanse",
            "subtitle": "A sprawling interstellar mystery",
            "year": 2015,
            "genres": ["Science Fiction", "Drama"],
            "badges": ["Critically Acclaimed"],
            "meta": {"source": "fallback"},
        },
        {
            "kind": "tv",
            "id": "fallback:tv:dark",
            "title": "Dark",
            "subtitle": "Time travel, secrets, and consequences",
            "year": 2017,
            "genres": ["Science Fiction", "Mystery"],
            "badges": ["International"],
            "meta": {"source": "fallback"},
        },
    ],
    "album": [
        {
            "kind": "album",
            "id": "fallback:album:kind-of-blue",
            "title": "Kind of Blue",
            "subtitle": "Miles Davis",
            "year": 1959,
            "genres": ["Jazz"],
            "badges": ["Essential"],
            "meta": {"source": "fallback"},
        },
        {
            "kind": "album",
            "id": "fallback:album:rumours",
            "title": "Rumours",
            "subtitle": "Fleetwood Mac",
            "year": 1977,
            "genres": ["Rock"],
            "badges": ["Classic"],
            "meta": {"source": "fallback"},
        },
    ],
}


async def _discover_video(
    media_type: Literal["movie", "tv"],
    sort: SortOption,
    page: int,
    metadata,
) -> PaginatedResponse[DiscoverItem]:
    path, params = _tmdb_discover_request(media_type, sort, page)
    try:
        payload = await metadata.tmdb(path, params=params, request_id=None)
    except MetadataProxyError as exc:
        detail = exc.detail or "tmdb_error"
        if (
            exc.status_code in {502, 503}
            and isinstance(detail, str)
            and detail == "tmdb_not_configured"
        ):
            logger.warning("discover: tmdb not configured for media_type=%s", media_type)
            payload = None
        else:
            logger.exception("discover: tmdb discovery failed media_type=%s", media_type)
            raise HTTPException(status_code=502, detail=detail) from exc
    except Exception:
        logger.exception("discover: tmdb discovery failed media_type=%s", media_type)
        payload = None

    if not payload or not isinstance(payload, dict):
        return _fallback_response(media_type, page)

    results = payload.get("results") or []
    items = [_map_tmdb_item(media_type, result, sort) for result in results]
    filtered = [item for item in items if item is not None]

    if not filtered:
        return _fallback_response(media_type, page)

    total_pages = _safe_int(payload.get("total_pages")) or 1
    current_page = _safe_int(payload.get("page")) or page

    return PaginatedResponse[DiscoverItem](page=current_page, total_pages=total_pages, items=filtered)


async def _discover_albums(
    sort: SortOption,
    page: int,
    metadata,
    musicbrainz: MusicBrainzClient,
) -> PaginatedResponse[DiscoverItem]:
    params = {
        "method": "chart.gettopalbums",
        "page": max(1, page),
        "limit": 50,
    }
    try:
        listing = await metadata.lastfm("chart.gettopalbums", params=params, request_id=None)
    except MetadataProxyError as exc:
        detail = exc.detail or "lastfm_error"
        if (
            exc.status_code in {502, 503}
            and isinstance(detail, str)
            and detail == "lastfm_not_configured"
        ):
            logger.warning("discover: lastfm not configured")
            return _fallback_response("album", page)
        logger.exception("discover: lastfm chart lookup failed page=%s", page)
        raise HTTPException(status_code=502, detail=detail) from exc
    except Exception:
        logger.exception("discover: lastfm chart lookup failed page=%s", page)
        return _fallback_response("album", page)

    if not isinstance(listing, dict):
        return _fallback_response("album", page)

    container = listing.get("albums") or listing.get("topalbums")
    if not isinstance(container, dict):
        return _fallback_response("album", page)

    raw_items = container.get("album") or []
    if not isinstance(raw_items, list):
        raw_items = []

    if sort == "az":
        raw_items = sorted(raw_items, key=lambda item: _slug_fragment(item.get("name")))

    items: list[DiscoverItem] = []
    for raw in raw_items:
        mapped = await _map_album_item(raw, musicbrainz)
        if mapped is not None:
            items.append(mapped)

    if not items:
        return _fallback_response("album", page)

    attrs = container.get("@attr") if isinstance(container, dict) else {}
    total_pages = _safe_int(attrs.get("totalPages")) or 1
    current_page = _safe_int(attrs.get("page")) or page

    return PaginatedResponse[DiscoverItem](page=current_page, total_pages=total_pages, items=items)


def _fallback_response(kind: Literal["movie", "tv", "album"], page: int) -> PaginatedResponse[DiscoverItem]:
    base = FALLBACK_PAYLOAD.get(kind, []) if page == 1 else []
    items = [DiscoverItem(**item) for item in base]
    return PaginatedResponse[DiscoverItem](page=page, total_pages=1, items=items)


def _map_tmdb_item(
    media_type: Literal["movie", "tv"],
    result: Any,
    sort: SortOption,
) -> DiscoverItem | None:
    if not isinstance(result, dict):
        return None
    tmdb_id = result.get("id")
    if tmdb_id is None:
        return None
    title = result.get("title") if media_type == "movie" else result.get("name")
    if not title:
        return None

    overview = result.get("overview")
    date_field = "release_date" if media_type == "movie" else "first_air_date"
    year = _year_from_date(result.get(date_field))
    poster = result.get("poster_path")
    backdrop = result.get("backdrop_path")
    vote_average = _safe_float(result.get("vote_average"))

    meta: dict[str, Any] = {
        "source": "tmdb",
        "tmdb_id": tmdb_id,
        "sort": sort,
        "popularity": result.get("popularity"),
        "vote_count": result.get("vote_count"),
    }
    media_type_value = result.get("media_type")
    if media_type_value and isinstance(media_type_value, str):
        meta["media_type"] = media_type_value

    badges: list[str] = []
    if result.get("adult"):
        badges.append("Adult")
    if sort == "new" and year is not None:
        badges.append("New Release")

    genres = result.get("genre_names")
    if not isinstance(genres, list):
        genres = []

    poster_url = f"{TMDB_IMAGE_BASE}{poster}" if poster else None
    backdrop_url = f"{TMDB_IMAGE_BASE}{backdrop}" if backdrop else None

    return DiscoverItem(
        kind=media_type,
        id=f"tmdb:{media_type}:{tmdb_id}",
        title=title,
        subtitle=overview,
        year=year,
        poster=poster_url,
        backdrop=backdrop_url,
        rating=vote_average,
        genres=genres,
        badges=badges,
        meta=meta,
    )


async def _map_album_item(raw: Any, musicbrainz: MusicBrainzClient) -> DiscoverItem | None:
    if not isinstance(raw, dict):
        return None
    title = raw.get("name")
    if not title:
        return None
    artist_info = raw.get("artist")
    if isinstance(artist_info, dict):
        artist_name = artist_info.get("name")
        artist_mbid = artist_info.get("mbid")
    else:
        artist_name = artist_info if isinstance(artist_info, str) else None
        artist_mbid = None

    attrs = raw.get("@attr") if isinstance(raw.get("@attr"), dict) else {}
    meta: dict[str, Any] = {
        "source": "lastfm",
        "rank": _safe_int(attrs.get("rank")),
        "playcount": _safe_int(raw.get("playcount")),
        "listeners": _safe_int(raw.get("listeners")),
        "url": raw.get("url"),
        "mbid": raw.get("mbid"),
    }

    poster = _select_lastfm_image(raw.get("image"))
    tags = _extract_tags(raw.get("tags"))

    year = None
    mb_meta: dict[str, Any] | None = None
    if musicbrainz is not None:
        try:
            mb_data = await musicbrainz.lookup_release_group(artist=artist_name, album=title)
        except Exception:
            logger.exception("discover: musicbrainz lookup failed album=%s", title)
            mb_data = None
        if isinstance(mb_data, dict):
            release_group = mb_data.get("release_group") or {}
            release_date = release_group.get("first_release_date")
            year = _year_from_date(release_date)
            mb_meta = {
                "release_group_id": release_group.get("id"),
                "primary_type": release_group.get("primary_type"),
            }
            artist_data = mb_data.get("artist") or {}
            if isinstance(artist_data, dict) and artist_data.get("id"):
                mb_meta["artist_id"] = artist_data.get("id")
    if mb_meta:
        meta["musicbrainz"] = mb_meta
    if artist_mbid:
        meta["artist_mbid"] = artist_mbid

    badges: list[str] = []
    rank_value = meta.get("rank")
    if isinstance(rank_value, int):
        badges.append(f"#{rank_value}")

    item_id = _album_identifier(title, artist_name, raw.get("mbid"))

    return DiscoverItem(
        kind="album",
        id=item_id,
        title=title,
        subtitle=artist_name,
        year=year,
        poster=poster,
        genres=tags,
        badges=badges,
        meta=meta,
    )


def _safe_int(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _safe_float(value: Any) -> float | None:
    try:
        return round(float(value), 1)
    except (TypeError, ValueError):
        return None


def _year_from_date(value: Any) -> int | None:
    if not isinstance(value, str) or len(value) < 4:
        return None
    try:
        return int(value[:4])
    except ValueError:
        return None


def _select_lastfm_image(images: Any) -> str | None:
    if not isinstance(images, list):
        return None
    preferred_order = ["mega", "extralarge", "large", "medium", "small"]
    ranked: list[tuple[int, str]] = []
    seen: set[str] = set()
    for image in images:
        if not isinstance(image, dict):
            continue
        url = image.get("#text")
        if not url or url in seen:
            continue
        seen.add(url)
        size = image.get("size")
        try:
            weight = preferred_order.index(size) if isinstance(size, str) else len(preferred_order)
        except ValueError:
            weight = len(preferred_order)
        ranked.append((weight, url))
    if not ranked:
        return None
    ranked.sort(key=lambda item: item[0])
    return ranked[0][1]


def _extract_tags(tags: Any) -> list[str]:
    if isinstance(tags, dict):
        tag_data = tags.get("tag")
    else:
        tag_data = tags
    if not isinstance(tag_data, list):
        return []
    collected = []
    for tag in tag_data:
        if isinstance(tag, dict):
            name = tag.get("name")
        else:
            name = tag if isinstance(tag, str) else None
        if name:
            collected.append(str(name))
    return collected


def _album_identifier(title: str, artist: str | None, mbid: Any) -> str:
    if isinstance(mbid, str) and mbid:
        return f"lastfm:{mbid}"
    base = f"{artist or 'unknown'}-{title}".lower()
    slug = "".join(ch if ch.isalnum() else "-" for ch in base)
    slug = "-".join(filter(None, slug.split("-")))
    return f"lastfm:{slug or 'album'}"


def _slug_fragment(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return value.lower()

