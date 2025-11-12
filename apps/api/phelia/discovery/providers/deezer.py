from __future__ import annotations

import asyncio
import os
import random
from typing import Any, Dict, List, Optional

import httpx

from ..models import AlbumItem, DiscoveryResponse
from .base import Provider

DEEZER_API_ROOT = "https://api.deezer.com"
COUNTRY_MAP = {"US": 2, "GB": 4, "FR": 0, "DE": 3, "GE": 82}


class DeezerProvider(Provider):
    name = "deezer"

    def __init__(self) -> None:
        self.timeout = float(os.getenv("DISCOVERY_HTTP_TIMEOUT", "8"))

    async def _get(
        self, path: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        retries = 2
        delay = 0.5
        last_error: Exception | None = None
        for attempt in range(retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.get(f"{DEEZER_API_ROOT}{path}", params=params)
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

    def _canonical_key(self, artist: str, title: str, release_date: str | None) -> str:
        artist_key = _slugify(artist)
        title_key = _slugify(title)
        year = (release_date or "")[:4]
        return f"{artist_key}::{title_key}::{year}"

    async def charts(self, *, market: Optional[str], limit: int) -> DiscoveryResponse:
        market = (market or os.getenv("DISCOVERY_DEFAULT_MARKET", "US")).upper()
        country_id = COUNTRY_MAP.get(market)
        path = (
            f"/chart/{country_id}/albums" if country_id is not None else "/chart/albums"
        )
        payload = await self._get(path, params={"limit": limit})
        data = payload.get("data", [])
        items: List[AlbumItem] = []
        for entry in data[:limit]:
            artist = (entry.get("artist") or {}).get("name") or ""
            title = entry.get("title") or ""
            if not artist or not title:
                continue
            items.append(
                AlbumItem(
                    id=str(entry.get("id")),
                    canonical_key=self._canonical_key(
                        artist, title, entry.get("release_date")
                    ),
                    source="deezer",
                    title=title,
                    artist=artist,
                    release_date=entry.get("release_date"),
                    cover_url=entry.get("cover_medium") or entry.get("cover"),
                    source_url=entry.get("link"),
                    market=market,
                    score=(
                        float(entry.get("position")) if entry.get("position") else None
                    ),
                    preview_url=entry.get("preview"),
                )
            )
        return DiscoveryResponse(provider="deezer", items=items)

    async def tags(self, *, tag: str, limit: int) -> DiscoveryResponse:
        raise NotImplementedError

    async def new_releases(
        self, *, market: Optional[str], limit: int
    ) -> DiscoveryResponse:
        # Deezer does not expose a dedicated new releases endpoint; reuse charts
        return await self.charts(market=market, limit=limit)

    async def search_albums(self, *, query: str, limit: int) -> DiscoveryResponse:
        payload = await self._get("/search/album", params={"q": query, "limit": limit})
        data = payload.get("data", [])
        items: List[AlbumItem] = []
        for entry in data[:limit]:
            artist = (entry.get("artist") or {}).get("name") or ""
            title = entry.get("title") or ""
            if not artist or not title:
                continue
            items.append(
                AlbumItem(
                    id=str(entry.get("id")),
                    canonical_key=self._canonical_key(
                        artist, title, entry.get("release_date")
                    ),
                    source="deezer",
                    title=title,
                    artist=artist,
                    release_date=entry.get("release_date"),
                    cover_url=entry.get("cover_medium") or entry.get("cover"),
                    source_url=entry.get("link"),
                    preview_url=entry.get("preview"),
                )
            )
        return DiscoveryResponse(provider="deezer", items=items)


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
