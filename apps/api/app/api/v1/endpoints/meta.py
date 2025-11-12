"""Metadata lookup endpoints for the web UI."""

from __future__ import annotations

import asyncio
import os
from typing import Any, Iterable, Literal

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.runtime_settings import runtime_settings
from app.schemas.media import Classification
from app.schemas.meta import (
    CanonicalPayload,
    MetaAlbumInfo,
    MetaCastMember,
    MetaDetail,
    MetaItemType,
    MetaSearchItem,
    MetaSearchResponse,
    MetaTrack,
    MetaTVInfo,
)
from app.services.meta.canonical import build_album, build_movie, build_tv
from app.services.metadata import (
    get_classifier,
    get_metadata_client,
    get_metadata_router,
)
from app.services.metadata.metadata_client import MetadataProxyError
from app.services.metadata.constants import TMDB_IMAGE_BASE
from app.services.metadata.providers.discogs import DiscogsClient


public_router = APIRouter(tags=["metadata"])


def _metadata_client():
    return get_metadata_client()


def _discogs_client() -> DiscogsClient:
    return DiscogsClient(token=runtime_settings.key_getter("discogs"))


def _extract_year(raw: Any) -> int | None:
    if isinstance(raw, int):
        return raw
    if isinstance(raw, str) and raw:
        try:
            return int(raw[:4])
        except (TypeError, ValueError):  # pragma: no cover - defensive
            return None
    return None


def _tmdb_search_item(
    result: dict[str, Any], media_type: Literal["movie", "tv"]
) -> tuple[float, MetaSearchItem] | None:
    tmdb_id = result.get("id")
    if tmdb_id is None:
        return None
    title = result.get("title") if media_type == "movie" else result.get("name")
    if not isinstance(title, str) or not title.strip():
        title = result.get("name") if media_type == "movie" else result.get("title")
    title = title or "Untitled"
    date_key = "release_date" if media_type == "movie" else "first_air_date"
    year = _extract_year(result.get(date_key))
    poster_path = result.get("poster_path")
    popularity = result.get("popularity")
    try:
        score = float(popularity)
    except (TypeError, ValueError):
        score = 0.0
    subtitle = result.get(date_key) or (f"{year}" if year else None)
    item = MetaSearchItem(
        type="movie" if media_type == "movie" else "tv",
        provider="tmdb",
        id=str(tmdb_id),
        title=title,
        subtitle=subtitle,
        year=year,
        poster=f"{TMDB_IMAGE_BASE}{poster_path}" if poster_path else None,
        extra={"tmdb_id": tmdb_id},
    )
    return score, item


def _discogs_search_item(result: dict[str, Any]) -> tuple[float, MetaSearchItem] | None:
    if not isinstance(result, dict):
        return None
    discogs_id = result.get("id")
    resource_type = result.get("type") or "master"
    if discogs_id is None:
        return None
    title = result.get("title") or "Untitled"
    artist = result.get("artist")
    if not artist and " - " in title:
        artist, _, maybe_album = title.partition(" - ")
        title = maybe_album.strip() or title
    year = _extract_year(result.get("year"))
    poster = result.get("cover_image") or result.get("thumb")
    score = result.get("score") or 0
    try:
        score_value = float(score)
    except (TypeError, ValueError):
        score_value = 0.0
    item = MetaSearchItem(
        type="album",
        provider="discogs",
        id=f"{resource_type}:{discogs_id}",
        title=title,
        subtitle=str(artist) if artist else None,
        year=year,
        poster=poster,
        extra={"resource_type": resource_type},
    )
    return score_value, item


def _lastfm_search_item(result: dict[str, Any]) -> tuple[float, MetaSearchItem] | None:
    name = result.get("name") if isinstance(result, dict) else None
    if not name:
        return None
    artist = result.get("artist") if isinstance(result, dict) else None
    images = result.get("image") if isinstance(result, dict) else None
    poster = None
    if isinstance(images, Iterable):
        for entry in images:
            if isinstance(entry, dict) and entry.get("#text"):
                poster = entry.get("#text")
        if not poster:
            for entry in images:
                if isinstance(entry, dict) and entry.get("#text"):
                    poster = entry.get("#text")
                    break
    listeners = result.get("listeners") if isinstance(result, dict) else None
    try:
        score = float(listeners)
    except (TypeError, ValueError):
        score = 0.0
    identifier = f"{artist or ''}|{name}"
    item = MetaSearchItem(
        type="album",
        provider="lastfm",
        id=identifier,
        title=name,
        subtitle=artist,
        poster=poster or None,
        extra={"url": result.get("url")},
    )
    return score, item


def _dedupe(
    items: list[tuple[float, MetaSearchItem]],
) -> list[tuple[float, MetaSearchItem]]:
    seen: set[tuple[str, str]] = set()
    unique: list[tuple[float, MetaSearchItem]] = []
    for score, item in items:
        key = (item.provider, item.id)
        if key in seen:
            continue
        seen.add(key)
        unique.append((score, item))
    return unique


@public_router.get("/search", response_model=MetaSearchResponse)
async def meta_search(
    q: str = Query(..., min_length=2),
    limit: int = Query(20, ge=1, le=50),
) -> MetaSearchResponse:
    metadata = _metadata_client()
    discogs = _discogs_client()

    async def _movies() -> list[tuple[float, MetaSearchItem]]:
        params = {
            "query": q,
            "include_adult": False,
            "language": "en-US",
            "page": 1,
        }
        try:
            response = await metadata.tmdb(
                "search/movie", params=params, request_id=None
            )
        except MetadataProxyError as exc:
            detail = exc.detail or "tmdb_error"
            if (
                exc.status_code in {502, 503}
                and isinstance(detail, str)
                and detail == "tmdb_not_configured"
            ):
                return []
            raise HTTPException(status_code=502, detail=detail) from exc
        if not isinstance(response, dict):
            return []
        results = response.get("results")
        if not isinstance(results, list):
            return []
        items: list[tuple[float, MetaSearchItem]] = []
        for result in results[:limit]:
            mapped = _tmdb_search_item(result, "movie")
            if mapped:
                items.append(mapped)
        return items

    async def _tv() -> list[tuple[float, MetaSearchItem]]:
        params = {
            "query": q,
            "include_adult": False,
            "language": "en-US",
            "page": 1,
        }
        try:
            response = await metadata.tmdb("search/tv", params=params, request_id=None)
        except MetadataProxyError as exc:
            detail = exc.detail or "tmdb_error"
            if (
                exc.status_code in {502, 503}
                and isinstance(detail, str)
                and detail == "tmdb_not_configured"
            ):
                return []
            raise HTTPException(status_code=502, detail=detail) from exc
        if not isinstance(response, dict):
            return []
        results = response.get("results")
        if not isinstance(results, list):
            return []
        items: list[tuple[float, MetaSearchItem]] = []
        for result in results[:limit]:
            mapped = _tmdb_search_item(result, "tv")
            if mapped:
                items.append(mapped)
        return items

    async def _albums() -> list[tuple[float, MetaSearchItem]]:
        hits: list[tuple[float, MetaSearchItem]] = []
        if discogs.token:
            results = await discogs.search_albums(q, limit=limit)
            for result in results:
                mapped = _discogs_search_item(result)
                if mapped:
                    hits.append(mapped)
        if hits:
            return hits

        params = {"method": "album.search", "album": q, "limit": limit}
        try:
            response = await metadata.lastfm(
                "album.search", params=params, request_id=None
            )
        except MetadataProxyError as exc:
            detail = exc.detail or "lastfm_error"
            if (
                exc.status_code in {502, 503}
                and isinstance(detail, str)
                and detail == "lastfm_not_configured"
            ):
                return hits
            if exc.status_code == 404:
                return hits
            raise HTTPException(status_code=502, detail=detail) from exc
        if not isinstance(response, dict):
            return hits
        results = response.get("results")
        matches = results.get("albummatches") if isinstance(results, dict) else None
        albums = matches.get("album") if isinstance(matches, dict) else []
        if not isinstance(albums, list):
            return hits
        for result in albums:
            mapped = _lastfm_search_item(result)
            if mapped:
                hits.append(mapped)
        return hits

    movie_task, tv_task, album_task = await asyncio.gather(_movies(), _tv(), _albums())
    combined = _dedupe(movie_task + tv_task + album_task)
    combined.sort(key=lambda item: item[0], reverse=True)
    limited = [item for _, item in combined[:limit]]
    return MetaSearchResponse(items=limited)


async def _tmdb_detail(
    request: Request, item_type: Literal["movie", "tv"], provider_id: str
) -> MetaDetail:
    metadata = _metadata_client()
    try:
        tmdb_id = int(provider_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="invalid_id") from None

    params = {
        "language": "en-US",
        "append_to_response": "external_ids,credits,recommendations,similar",
    }
    request_id = request.headers.get("x-request-id")
    try:
        payload = await (
            metadata.tmdb(f"movie/{tmdb_id}", params=params, request_id=request_id)
            if item_type == "movie"
            else metadata.tmdb(f"tv/{tmdb_id}", params=params, request_id=request_id)
        )
    except MetadataProxyError as exc:
        detail = exc.detail or "tmdb_error"
        if exc.status_code == 404:
            raise HTTPException(status_code=404, detail="not_found") from exc
        if exc.status_code in {400, 401, 403, 422}:
            raise HTTPException(status_code=exc.status_code, detail=detail) from exc
        if (
            exc.status_code in {502, 503}
            and isinstance(detail, str)
            and detail == "tmdb_not_configured"
        ):
            raise HTTPException(status_code=502, detail="tmdb_not_configured") from exc
        raise HTTPException(status_code=502, detail=detail) from exc

    if not isinstance(payload, dict):
        raise HTTPException(status_code=502, detail="tmdb_invalid_response")

    title = payload.get("title") if item_type == "movie" else payload.get("name")
    if not isinstance(title, str) or not title.strip():
        title = payload.get("name") if item_type == "movie" else payload.get("title")
    title = title or "Untitled"
    date_key = "release_date" if item_type == "movie" else "first_air_date"
    year = _extract_year(payload.get(date_key))
    poster = payload.get("poster_path")
    backdrop = payload.get("backdrop_path")
    overview = payload.get("overview")
    genres_raw = payload.get("genres") if isinstance(payload, dict) else None
    genres: list[str] = []
    if isinstance(genres_raw, Iterable):
        for entry in genres_raw:
            if isinstance(entry, dict) and entry.get("name"):
                genres.append(str(entry["name"]))
    runtime = payload.get("runtime") if item_type == "movie" else None
    if runtime is None and item_type == "tv":
        run_list = payload.get("episode_run_time")
        if isinstance(run_list, Iterable):
            for value in run_list:
                try:
                    runtime = int(value)
                    break
                except (TypeError, ValueError):  # pragma: no cover - defensive
                    continue
    vote_average = payload.get("vote_average")
    try:
        rating = float(vote_average) if vote_average is not None else None
    except (TypeError, ValueError):
        rating = None
    credits = payload.get("credits") if isinstance(payload, dict) else None
    cast_members: list[MetaCastMember] = []
    cast_raw = credits.get("cast") if isinstance(credits, dict) else None
    if isinstance(cast_raw, Iterable):
        for member in list(cast_raw)[:10]:
            if not isinstance(member, dict):
                continue
            name = member.get("name") or member.get("original_name")
            if not name:
                continue
            cast_members.append(
                MetaCastMember(name=name, character=member.get("character"))
            )

    fallback = title
    if item_type == "movie":
        query, movie_payload = build_movie(title, year, fallback)
        canonical = CanonicalPayload(query=query or fallback, movie=movie_payload)
    else:
        query, tv_payload = build_tv(title, None, None, fallback)
        canonical = CanonicalPayload(query=query or fallback, tv=tv_payload)

    tv_info = None
    if item_type == "tv":
        seasons = payload.get("number_of_seasons")
        episodes = payload.get("number_of_episodes")
        seasons_int = seasons if isinstance(seasons, int) else None
        episodes_int = episodes if isinstance(episodes, int) else None
        tv_info = MetaTVInfo(seasons=seasons_int, episodes=episodes_int)

    return MetaDetail(
        type=item_type,
        title=title,
        year=year,
        poster=f"{TMDB_IMAGE_BASE}{poster}" if poster else None,
        backdrop=f"{TMDB_IMAGE_BASE}{backdrop}" if backdrop else None,
        synopsis=overview,
        genres=genres,
        runtime=runtime,
        rating=rating,
        cast=cast_members,
        tv=tv_info,
        canonical=canonical,
    )


async def _fetch_lastfm_album(
    request: Request, artist: str | None, album: str
) -> dict[str, Any] | None:
    metadata = _metadata_client()
    params: dict[str, Any] = {"album": album}
    if artist:
        params["artist"] = artist
    try:
        response = await metadata.lastfm(
            "album.getinfo",
            params=params,
            request_id=request.headers.get("x-request-id"),
        )
    except MetadataProxyError as exc:
        detail = exc.detail or "lastfm_error"
        if exc.status_code == 404:
            return None
        if (
            exc.status_code in {502, 503}
            and isinstance(detail, str)
            and detail == "lastfm_not_configured"
        ):
            raise HTTPException(
                status_code=502, detail="lastfm_not_configured"
            ) from exc
        raise HTTPException(status_code=502, detail=detail) from exc

    if not isinstance(response, dict):
        return None
    album_data = response.get("album")
    if not isinstance(album_data, dict):
        return None

    tags_container = album_data.get("tags") or {}
    tag_entries = (
        tags_container.get("tag") if isinstance(tags_container, dict) else None
    )
    tag_list: list[str] = []
    if isinstance(tag_entries, Iterable):
        for entry in tag_entries:
            if isinstance(entry, dict) and entry.get("name"):
                tag_list.append(str(entry["name"]))

    wiki = album_data.get("wiki")
    if not isinstance(wiki, dict):
        wiki = {}

    def _to_int(value: Any) -> int | None:
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    return {
        "tags": tag_list,
        "listeners": _to_int(album_data.get("listeners")),
        "playcount": _to_int(album_data.get("playcount")),
        "summary": wiki.get("summary"),
        "url": album_data.get("url"),
        "extra": album_data,
    }


async def _discogs_detail(request: Request, provider_id: str) -> MetaDetail:
    discogs = _discogs_client()
    if not discogs.token:
        raise HTTPException(status_code=502, detail="discogs_not_configured")

    prefix, _, raw_id = provider_id.partition(":")
    if not raw_id:
        raw_id = prefix
        prefix = "master"
    resource_path: str
    if prefix == "master":
        resource_path = f"{discogs.base_url}/masters/{raw_id}"
    elif prefix == "release":
        resource_path = f"{discogs.base_url}/releases/{raw_id}"
    else:
        raise HTTPException(status_code=422, detail="invalid_id")

    payload = await discogs.fetch_resource(resource_path)
    if not payload:
        raise HTTPException(status_code=404, detail="not_found")

    title = payload.get("title") or "Untitled"
    year = _extract_year(payload.get("year"))
    images = payload.get("images") if isinstance(payload, dict) else None
    poster = None
    if isinstance(images, Iterable):
        for image in images:
            if isinstance(image, dict) and image.get("uri"):
                poster = image.get("uri")
                break
    genres = []
    styles = []
    for field_name, target in (("genres", genres), ("styles", styles)):
        values = payload.get(field_name)
        if isinstance(values, Iterable):
            for value in values:
                if isinstance(value, str):
                    target.append(value)
    tracklist_raw = payload.get("tracklist")
    tracks: list[MetaTrack] = []
    if isinstance(tracklist_raw, Iterable):
        for entry in tracklist_raw:
            if not isinstance(entry, dict):
                continue
            title_value = entry.get("title")
            if not isinstance(title_value, str) or not title_value.strip():
                continue
            tracks.append(
                MetaTrack(
                    position=entry.get("position"),
                    title=title_value,
                    duration=entry.get("duration"),
                )
            )

    artists = payload.get("artists")
    artist_name = None
    if isinstance(artists, Iterable):
        for artist in artists:
            if isinstance(artist, dict) and artist.get("name"):
                artist_name = artist.get("name")
                break

    summary = None
    if artist_name:
        try:
            info = await _fetch_lastfm_album(request, artist_name, title)
        except HTTPException as exc:
            if exc.status_code == 502 and exc.detail == "lastfm_not_configured":
                info = None
            else:
                raise
        if info:
            summary = info.get("summary") or summary
            tags = info.get("tags")
            if isinstance(tags, Iterable):
                for tag in tags:
                    if isinstance(tag, str) and tag not in styles:
                        styles.append(tag)

    album_payload = MetaAlbumInfo(
        artist=artist_name or "",
        album=title,
        year=year,
        styles=styles,
        tracklist=tracks,
    )

    query, canonical_album = build_album(artist_name, title, year, title)
    canonical = CanonicalPayload(query=query or title, album=canonical_album)

    return MetaDetail(
        type="album",
        title=title,
        year=year,
        poster=poster,
        synopsis=summary or payload.get("notes"),
        genres=genres,
        runtime=None,
        rating=None,
        cast=[],
        album=album_payload,
        canonical=canonical,
    )


async def _lastfm_detail(request: Request, provider_id: str) -> MetaDetail:
    artist, _, album = provider_id.partition("|")
    if not album:
        raise HTTPException(status_code=422, detail="invalid_id")
    info = await _fetch_lastfm_album(request, artist or None, album)
    if not info:
        raise HTTPException(status_code=404, detail="not_found")
    tracklist_raw = (
        info.get("extra", {}).get("tracks", {}).get("track")
        if isinstance(info, dict)
        else None
    )
    tracks: list[MetaTrack] = []
    if isinstance(tracklist_raw, Iterable):
        for entry in tracklist_raw:
            if not isinstance(entry, dict):
                continue
            name = entry.get("name")
            if not isinstance(name, str) or not name:
                continue
            tracks.append(
                MetaTrack(
                    position=(
                        str(entry.get("@attr", {}).get("rank"))
                        if isinstance(entry.get("@attr"), dict)
                        else None
                    ),
                    title=name,
                    duration=(
                        str(entry.get("duration")) if entry.get("duration") else None
                    ),
                )
            )
    styles = []
    tags = info.get("tags") if isinstance(info, dict) else None
    if isinstance(tags, Iterable):
        for tag in tags:
            if isinstance(tag, str):
                styles.append(tag)
    images = info.get("extra", {}).get("image") if isinstance(info, dict) else None
    poster = None
    if isinstance(images, Iterable):
        for entry in images:
            if isinstance(entry, dict) and entry.get("#text"):
                poster = entry.get("#text")
    query, canonical_album = build_album(artist, album, None, f"{artist} - {album}")
    canonical = CanonicalPayload(
        query=query or f"{artist} - {album}", album=canonical_album
    )
    album_payload = MetaAlbumInfo(
        artist=artist or "",
        album=album,
        styles=styles,
        tracklist=tracks,
    )
    return MetaDetail(
        type="album",
        title=album,
        poster=poster,
        synopsis=info.get("summary") if isinstance(info, dict) else None,
        genres=[],
        runtime=None,
        rating=None,
        cast=[],
        album=album_payload,
        canonical=canonical,
    )


@public_router.get("/detail", response_model=MetaDetail)
async def meta_detail(
    request: Request,
    *,
    type: MetaItemType,
    id: str,
    provider: str,
) -> MetaDetail:
    if type in {"movie", "tv"}:
        if provider != "tmdb":
            raise HTTPException(status_code=422, detail="unsupported_provider")
        return await _tmdb_detail(request, type, id)
    if type == "album":
        if provider == "discogs":
            return await _discogs_detail(request, id)
        if provider == "lastfm":
            return await _lastfm_detail(request, id)
        raise HTTPException(status_code=422, detail="unsupported_provider")
    raise HTTPException(status_code=422, detail="unsupported_type")


class LookupRequest(BaseModel):
    title: str = Field(..., min_length=1)
    hint: Literal["music", "movie", "tv", "other", "auto"] = "auto"


@public_router.post("/lookup")
async def lookup(body: LookupRequest) -> dict[str, Any]:
    classifier = get_classifier()
    router_service = get_metadata_router()

    if body.hint == "auto":
        classification = classifier.classify_torrent(body.title)
    else:
        classification = Classification(
            type=body.hint if body.hint != "auto" else "other",
            confidence=0.99,
            reasons=[f"hint:{body.hint}"],
        )
    card = await router_service.enrich(classification, body.title)
    return card.model_dump()


@public_router.get("/providers/status")
def providers_status() -> dict[str, Any]:
    discovery = {
        "lastfm": runtime_settings.is_configured("lastfm"),
        "deezer": os.getenv("DEEZER_ENABLED", "true").lower() == "true",
        "itunes": os.getenv("ITUNES_ENABLED", "true").lower() == "true",
        "musicbrainz": os.getenv("MUSICBRAINZ_ENABLED", "true").lower() == "true",
        "listenbrainz": runtime_settings.is_configured("listenbrainz"),
        "spotify": (
            runtime_settings.is_configured("spotify_client_id")
            and runtime_settings.is_configured("spotify_client_secret")
        ),
    }
    return {
        "tmdb": True,
        "omdb": runtime_settings.omdb_enabled,
        "discogs": runtime_settings.discogs_enabled,
        "lastfm": True,
        "musicbrainz": bool(settings.MB_USER_AGENT),
        "discovery": discovery,
    }


router = APIRouter(tags=["metadata"])
router.include_router(public_router, prefix="/meta")
router.include_router(public_router)
