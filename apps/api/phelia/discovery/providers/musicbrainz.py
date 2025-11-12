from __future__ import annotations

import asyncio
import os
import time
from typing import Dict, List, Optional

import httpx

from ..models import AlbumItem, DiscoveryResponse
from .base import Provider

MB_API_ROOT = "https://musicbrainz.org/ws/2"
MB_USER_AGENT = os.getenv("MB_USER_AGENT", "Phelia/1.0 (https://example.local)")
METADATA_BASE_URL = os.getenv("METADATA_BASE_URL")
_RATE_LIMIT = 1.0  # one request per second
_last_request = 0.0
_lock = asyncio.Lock()


async def _rate_limit_wait() -> None:
    global _last_request
    async with _lock:
        now = time.monotonic()
        delta = now - _last_request
        if delta < 1 / _RATE_LIMIT:
            await asyncio.sleep((1 / _RATE_LIMIT) - delta)
        _last_request = time.monotonic()


class MusicBrainzProvider(Provider):
    name = "musicbrainz"

    def __init__(self) -> None:
        self.timeout = float(os.getenv("DISCOVERY_HTTP_TIMEOUT", "8"))
        self._metadata_base_url = (METADATA_BASE_URL or "").rstrip("/") or None

    async def _get(self, path: str, params: Dict[str, str]) -> Dict[str, object]:
        await _rate_limit_wait()
        if self._metadata_base_url:
            url = f"{self._metadata_base_url}/mb/{path.lstrip('/')}"
            headers = {"Accept": "application/json"}
        else:
            url = f"{MB_API_ROOT}{path}"
            headers = {"Accept": "application/json", "User-Agent": MB_USER_AGENT}
        async with httpx.AsyncClient(timeout=self.timeout, headers=headers) as client:
            resp = await client.get(url, params=params)
        if resp.status_code == 503:
            retry_after = resp.headers.get("Retry-After")
            if retry_after and retry_after.isdigit():
                await asyncio.sleep(int(retry_after))
            return {}
        resp.raise_for_status()
        return resp.json()

    async def charts(self, *, market: Optional[str], limit: int) -> DiscoveryResponse:
        raise NotImplementedError

    async def tags(self, *, tag: str, limit: int) -> DiscoveryResponse:
        raise NotImplementedError

    async def new_releases(
        self, *, market: Optional[str], limit: int
    ) -> DiscoveryResponse:
        raise NotImplementedError

    async def search_albums(self, *, query: str, limit: int) -> DiscoveryResponse:
        params = {
            "query": query,
            "fmt": "json",
            "limit": str(limit),
            "type": "release-group",
        }
        data = await self._get("/release-group", params)
        groups = data.get("release-groups", []) if isinstance(data, dict) else []
        items: List[AlbumItem] = []
        for entry in groups[:limit]:
            title = entry.get("title")
            artist_credit = entry.get("artist-credit") or []
            artist = ""
            if artist_credit:
                artist = artist_credit[0].get("name", "")
            if not title or not artist:
                continue
            release_date = entry.get("first-release-date")
            items.append(
                AlbumItem(
                    id=str(entry.get("id")),
                    canonical_key=_canonical_key(artist, title, release_date),
                    source="musicbrainz",
                    title=title,
                    artist=artist,
                    release_date=release_date,
                    tags=[
                        tag.get("name")
                        for tag in entry.get("tags", [])
                        if tag.get("name")
                    ],
                    source_url=f"https://musicbrainz.org/release-group/{entry.get('id')}",
                )
            )
        return DiscoveryResponse(provider="musicbrainz", items=items)

    async def enrich(
        self, artist: str, title: str
    ) -> Optional[dict[str, Optional[str]]]:
        params = {
            "query": f"artist:{artist} AND release:{title}",
            "fmt": "json",
            "limit": "1",
            "type": "release-group",
        }
        data = await self._get("/release-group", params)
        groups = data.get("release-groups", []) if isinstance(data, dict) else []
        if not groups:
            return None
        group = groups[0]
        release_date = group.get("first-release-date")
        mbid = group.get("id")
        cover_url = None
        if mbid:
            cover_url = f"https://coverartarchive.org/release-group/{mbid}/front-500"
        return {
            "release_date": release_date,
            "cover_url": cover_url,
            "source_url": (
                f"https://musicbrainz.org/release-group/{mbid}" if mbid else None
            ),
        }


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
