from __future__ import annotations

import asyncio
import os
from collections.abc import Iterable
from typing import Dict, List, Optional

from app.core.runtime_settings import runtime_settings

from .cache import build_cache_key, cache_get_json, cache_set_json
from .models import AlbumItem, DiscoveryResponse, ProvidersStatus
from .providers.base import Provider
from .providers.deezer import DeezerProvider
from .providers.itunes import ITunesProvider
from .providers.lastfm import LastFMProvider
from .providers.listenbrainz import ListenBrainzProvider
from .providers.musicbrainz import MusicBrainzProvider
from .providers.spotify import SpotifyProvider

SOURCE_PRIORITY = {
    "spotify": 0,
    "deezer": 1,
    "lastfm": 2,
    "itunes": 3,
    "musicbrainz": 4,
    "listenbrainz": 5,
}

_PROVIDER_CACHE: Dict[str, Provider] = {}


def _slugify(value: str) -> str:
    normalized = value.lower().strip()
    cleaned: List[str] = []
    prev_dash = False
    for ch in normalized:
        if ch.isalnum():
            cleaned.append(ch)
            prev_dash = False
        else:
            if not prev_dash:
                cleaned.append("-")
                prev_dash = True
    return "".join(cleaned).strip("-")


def _canonical_key(item: AlbumItem) -> str:
    if item.canonical_key:
        return item.canonical_key
    year = (item.release_date or "")[:4]
    return f"{_slugify(item.artist)}::{_slugify(item.title)}::{year}"


def _provider_enabled(name: str) -> bool:
    env = os.getenv
    if name == "lastfm":
        return runtime_settings.is_configured("lastfm")
    if name == "deezer":
        return env("DEEZER_ENABLED", "true").lower() == "true"
    if name == "itunes":
        return env("ITUNES_ENABLED", "true").lower() == "true"
    if name == "musicbrainz":
        return env("MUSICBRAINZ_ENABLED", "true").lower() == "true"
    if name == "listenbrainz":
        return runtime_settings.is_configured("listenbrainz")
    if name == "spotify":
        return runtime_settings.is_configured(
            "spotify_client_id"
        ) and runtime_settings.is_configured("spotify_client_secret")
    return False


def _get_provider(name: str) -> Optional[Provider]:
    if not _provider_enabled(name):
        return None
    if name in _PROVIDER_CACHE:
        return _PROVIDER_CACHE[name]
    try:
        if name == "lastfm":
            provider = LastFMProvider(runtime_settings.key_getter("lastfm"))
        elif name == "deezer":
            provider = DeezerProvider()
        elif name == "itunes":
            provider = ITunesProvider()
        elif name == "musicbrainz":
            provider = MusicBrainzProvider()
        elif name == "listenbrainz":
            provider = ListenBrainzProvider(runtime_settings.key_getter("listenbrainz"))
        elif name == "spotify":
            provider = SpotifyProvider(
                client_id_getter=runtime_settings.key_getter("spotify_client_id"),
                client_secret_getter=runtime_settings.key_getter(
                    "spotify_client_secret"
                ),
            )
        else:
            return None
    except Exception:  # noqa: BLE001
        return None
    _PROVIDER_CACHE[name] = provider
    return provider


async def _call_provider(
    provider: Provider, method: str, kwargs: Dict[str, object]
) -> List[AlbumItem]:
    cache_key = build_cache_key(provider.name, method, kwargs)
    cached = await cache_get_json(cache_key)
    if cached:
        response = DiscoveryResponse(**cached)
        return [
            AlbumItem(**item) if not isinstance(item, AlbumItem) else item
            for item in response.items
        ]
    try:
        fn = getattr(provider, method)
        response: DiscoveryResponse = await fn(**kwargs)  # type: ignore[misc]
    except NotImplementedError:
        return []
    except Exception:
        return []
    await cache_set_json(cache_key, response.model_dump(mode="json"))
    return response.items


def _merge_items(responses: Iterable[AlbumItem]) -> List[AlbumItem]:
    merged: Dict[str, AlbumItem] = {}
    for item in responses:
        key = _canonical_key(item)
        existing = merged.get(key)
        if existing is None:
            merged[key] = item
            continue
        merged[key] = _prefer_item(existing, item)
    return list(merged.values())


def _prefer_item(current: AlbumItem, candidate: AlbumItem) -> AlbumItem:
    chosen = current
    if (
        (not current.cover_url and candidate.cover_url)
        or (
            (current.release_date or "") < (candidate.release_date or "")
            and candidate.release_date
        )
        or ((current.score or 0.0) < (candidate.score or 0.0))
        or (
            SOURCE_PRIORITY.get(candidate.source, 99)
            < SOURCE_PRIORITY.get(current.source, 99)
        )
    ):
        chosen = candidate
    base = AlbumItem(**chosen.model_dump())
    tags = set(current.tags)
    tags.update(candidate.tags)
    base.tags = list(tags)
    if not base.cover_url:
        base.cover_url = candidate.cover_url or current.cover_url
    if not base.release_date:
        base.release_date = candidate.release_date or current.release_date
    if not base.source_url:
        base.source_url = candidate.source_url or current.source_url
    if not base.preview_url:
        base.preview_url = candidate.preview_url or current.preview_url
    base.extra = {**current.extra, **candidate.extra, **base.extra}
    return base


async def _enrich_items(items: List[AlbumItem]) -> None:
    need_itunes = [item for item in items if not item.cover_url][:10]
    need_mb = [item for item in items if not item.release_date][:10]
    itunes = _get_provider("itunes")
    musicbrainz = _get_provider("musicbrainz")
    if itunes:
        for item in need_itunes:
            try:
                matches = await itunes.lookup_album(item.artist, item.title, limit=3)  # type: ignore[arg-type]
            except Exception:
                continue
            if not matches:
                continue
            match = matches[0]
            if match.cover_url and not item.cover_url:
                item.cover_url = match.cover_url
            if match.release_date and not item.release_date:
                item.release_date = match.release_date
            if match.source_url and not item.source_url:
                item.source_url = match.source_url
    if musicbrainz:
        for item in need_mb:
            try:
                enriched = await musicbrainz.enrich(item.artist, item.title)  # type: ignore[attr-defined]
            except Exception:
                continue
            if not enriched:
                continue
            if enriched.get("release_date") and not item.release_date:
                item.release_date = enriched["release_date"]
            if enriched.get("cover_url") and not item.cover_url:
                item.cover_url = enriched["cover_url"]
            if enriched.get("source_url") and not item.source_url:
                item.source_url = enriched["source_url"]


def _max_limit(limit: int) -> int:
    max_items = int(os.getenv("DISCOVERY_MAX_ITEMS", "50"))
    return min(limit, max_items)


async def get_charts(*, market: Optional[str], limit: int) -> List[AlbumItem]:
    limit = _max_limit(limit)
    market = market or os.getenv("DISCOVERY_DEFAULT_MARKET", "US")
    tasks: List[asyncio.Task[List[AlbumItem]]] = []
    for name in ("deezer", "spotify"):
        provider = _get_provider(name)
        if not provider:
            continue
        tasks.append(
            asyncio.create_task(
                _call_provider(provider, "charts", {"market": market, "limit": limit})
            )
        )
    results = await asyncio.gather(*tasks) if tasks else []
    merged = _merge_items(item for group in results for item in group)
    await _enrich_items(merged)
    return merged[:limit]


async def get_tag(*, tag: str, limit: int) -> List[AlbumItem]:
    limit = _max_limit(limit)
    tasks: List[asyncio.Task[List[AlbumItem]]] = []
    for name in ("lastfm", "listenbrainz"):
        provider = _get_provider(name)
        if not provider:
            continue
        tasks.append(
            asyncio.create_task(
                _call_provider(provider, "tags", {"tag": tag, "limit": limit})
            )
        )
    results = await asyncio.gather(*tasks) if tasks else []
    merged = _merge_items(item for group in results for item in group)
    await _enrich_items(merged)
    return merged[:limit]


async def get_new_releases(*, market: Optional[str], limit: int) -> List[AlbumItem]:
    limit = _max_limit(limit)
    market = market or os.getenv("DISCOVERY_DEFAULT_MARKET", "US")
    tasks: List[asyncio.Task[List[AlbumItem]]] = []
    for name in ("spotify", "deezer"):
        provider = _get_provider(name)
        if not provider:
            continue
        tasks.append(
            asyncio.create_task(
                _call_provider(
                    provider, "new_releases", {"market": market, "limit": limit}
                )
            )
        )
    results = await asyncio.gather(*tasks) if tasks else []
    merged = _merge_items(item for group in results for item in group)
    await _enrich_items(merged)
    return merged[:limit]


async def quick_search(*, query: str, limit: int) -> List[AlbumItem]:
    limit = _max_limit(limit)
    tasks: List[asyncio.Task[List[AlbumItem]]] = []
    for name in ("spotify", "deezer", "lastfm", "itunes", "musicbrainz"):
        provider = _get_provider(name)
        if not provider:
            continue
        tasks.append(
            asyncio.create_task(
                _call_provider(
                    provider, "search_albums", {"query": query, "limit": limit}
                )
            )
        )
    results = await asyncio.gather(*tasks) if tasks else []
    merged = _merge_items(item for group in results for item in group)
    await _enrich_items(merged)
    return merged[:limit]


async def providers_status() -> ProvidersStatus:
    return ProvidersStatus(
        lastfm=_provider_enabled("lastfm"),
        deezer=_provider_enabled("deezer"),
        itunes=_provider_enabled("itunes"),
        musicbrainz=_provider_enabled("musicbrainz"),
        listenbrainz=_provider_enabled("listenbrainz"),
        spotify=_provider_enabled("spotify"),
    )
