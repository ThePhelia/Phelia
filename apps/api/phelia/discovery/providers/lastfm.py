from __future__ import annotations

import asyncio
import os
import random
from collections.abc import Callable
from typing import Any, Dict, List, Optional

import httpx

from ..models import AlbumItem, DiscoveryResponse
from .base import Provider

LASTFM_API_ROOT = "https://ws.audioscrobbler.com/2.0/"


class LastFMProvider(Provider):
    name = "lastfm"

    def __init__(self, api_key_getter: Callable[[], Optional[str]]) -> None:
        self._api_key_getter = api_key_getter
        if not self._api_key_getter():
            raise RuntimeError("LASTFM_API_KEY missing")
        self.timeout = float(os.getenv("DISCOVERY_HTTP_TIMEOUT", "8"))

    async def _request(self, params: Dict[str, Any]) -> Dict[str, Any]:
        api_key = self._api_key_getter()
        if not api_key:
            raise RuntimeError("LASTFM_API_KEY missing")
        params = {**params, "api_key": api_key, "format": "json"}
        retries = 2
        delay = 0.5
        last_error: Exception | None = None
        for attempt in range(retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.get(LASTFM_API_ROOT, params=params)
                resp.raise_for_status()
                return resp.json()
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if attempt >= retries:
                    break
                jitter = random.uniform(0, 0.3)
                await asyncio.sleep(delay + jitter)
                delay *= 2
        if last_error:
            raise last_error
        return {}

    @staticmethod
    def _canonical_key(artist: str, title: str, release: str | None = None) -> str:
        artist_key = _slugify(artist)
        title_key = _slugify(title)
        year = (release or "")[:4]
        return f"{artist_key}::{title_key}::{year}"

    async def charts(self, *, market: Optional[str], limit: int) -> DiscoveryResponse:
        raise NotImplementedError

    async def tags(self, *, tag: str, limit: int) -> DiscoveryResponse:
        data = await self._request(
            {
                "method": "tag.gettopalbums",
                "tag": tag,
                "limit": limit,
            }
        )
        albums = data.get("albums", {}).get("album", [])
        items: List[AlbumItem] = []
        for album in albums[:limit]:
            artist = (album.get("artist") or {}).get("name") or ""
            title = album.get("name") or ""
            if not artist or not title:
                continue
            mbid = album.get("mbid") or album.get("url")
            images = album.get("image") or []
            cover = None
            for img in reversed(images):
                if img.get("#text"):
                    cover = img.get("#text")
                    break
            items.append(
                AlbumItem(
                    id=str(mbid),
                    canonical_key=self._canonical_key(
                        artist, title, album.get("releasedate")
                    ),
                    source="lastfm",
                    title=title,
                    artist=artist,
                    release_date=(album.get("releasedate") or "").strip() or None,
                    cover_url=cover,
                    source_url=album.get("url"),
                    tags=[tag],
                    score=(
                        float(album.get("playcount"))
                        if album.get("playcount")
                        else None
                    ),
                )
            )
        return DiscoveryResponse(provider="lastfm", items=items)

    async def new_releases(
        self, *, market: Optional[str], limit: int
    ) -> DiscoveryResponse:
        raise NotImplementedError

    async def search_albums(self, *, query: str, limit: int) -> DiscoveryResponse:
        data = await self._request(
            {
                "method": "album.search",
                "album": query,
                "autocorrect": 1,
                "limit": limit,
            }
        )
        results = data.get("results", {}).get("albummatches", {}).get("album", [])
        items: List[AlbumItem] = []
        for album in results[:limit]:
            artist = album.get("artist") or ""
            title = album.get("name") or ""
            if not artist or not title:
                continue
            items.append(
                AlbumItem(
                    id=album.get("mbid") or album.get("url") or f"{artist}-{title}",
                    canonical_key=self._canonical_key(artist, title, None),
                    source="lastfm",
                    title=title,
                    artist=artist,
                    source_url=album.get("url"),
                    cover_url=(
                        album.get("image", [{}])[-1].get("#text")
                        if album.get("image")
                        else None
                    ),
                )
            )
        return DiscoveryResponse(provider="lastfm", items=items)


def _slugify(value: str) -> str:
    normalized = value.lower().strip()
    cleaned = []
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
