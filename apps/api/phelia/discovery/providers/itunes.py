from __future__ import annotations

import asyncio
import os
import random
from typing import Any, Dict, List, Optional

import httpx

from ..models import AlbumItem, DiscoveryResponse
from .base import Provider

ITUNES_API_ROOT = "https://itunes.apple.com"


class ITunesProvider(Provider):
    name = "itunes"

    def __init__(self) -> None:
        self.timeout = float(os.getenv("DISCOVERY_HTTP_TIMEOUT", "8"))

    async def _get(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        retries = 2
        delay = 0.5
        last_error: Exception | None = None
        for attempt in range(retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.get(f"{ITUNES_API_ROOT}{path}", params=params)
                resp.raise_for_status()
                return resp.json()
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if attempt >= retries:
                    break
                await asyncio.sleep(delay + random.uniform(0, 0.3))
                delay *= 2
        if last_error:
            raise last_error
        return {}

    async def charts(self, *, market: Optional[str], limit: int) -> DiscoveryResponse:
        raise NotImplementedError

    async def tags(self, *, tag: str, limit: int) -> DiscoveryResponse:
        raise NotImplementedError

    async def new_releases(
        self, *, market: Optional[str], limit: int
    ) -> DiscoveryResponse:
        raise NotImplementedError

    async def search_albums(self, *, query: str, limit: int) -> DiscoveryResponse:
        payload = await self._get(
            "/search",
            {
                "term": query,
                "entity": "album",
                "limit": limit,
                "media": "music",
            },
        )
        results = payload.get("results", [])
        items: List[AlbumItem] = []
        for entry in results[:limit]:
            artist = entry.get("artistName") or ""
            title = entry.get("collectionName") or ""
            if not artist or not title:
                continue
            release_date = entry.get("releaseDate")
            items.append(
                AlbumItem(
                    id=str(
                        entry.get("collectionId")
                        or entry.get("collectionViewUrl")
                        or f"{artist}-{title}"
                    ),
                    canonical_key=_canonical_key(artist, title, release_date),
                    source="itunes",
                    title=title,
                    artist=artist,
                    release_date=(
                        release_date[:10]
                        if isinstance(release_date, str)
                        else release_date
                    ),
                    cover_url=entry.get("artworkUrl100"),
                    source_url=entry.get("collectionViewUrl"),
                    market=entry.get("country"),
                    preview_url=entry.get("previewUrl"),
                )
            )
        return DiscoveryResponse(provider="itunes", items=items)

    async def lookup_album(
        self, artist: str, title: str, limit: int = 5
    ) -> List[AlbumItem]:
        query = f"{artist} {title}".strip()
        response = await self.search_albums(query=query, limit=limit)
        return response.items


def _canonical_key(artist: str, title: str, release: Optional[str]) -> str:
    artist_key = _slugify(artist)
    title_key = _slugify(title)
    year = (release or "")[:4]
    return f"{artist_key}::{title_key}::{year}"


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
