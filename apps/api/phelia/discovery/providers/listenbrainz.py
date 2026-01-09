from __future__ import annotations

from collections.abc import Callable
from typing import Optional

import httpx

from ..models import AlbumItem, DiscoveryResponse
from .base import Provider


class ListenBrainzProvider(Provider):
    name = "listenbrainz"

    def __init__(self, token_getter: Callable[[], Optional[str]]) -> None:
        self._token_getter = token_getter
        if not self._token_getter():
            raise RuntimeError("ListenBrainz token missing")
        self.base_url = "https://api.listenbrainz.org/1"
        self.timeout = 8.0

    @property
    def token(self) -> str:
        token = self._token_getter()
        if not token:
            raise RuntimeError("ListenBrainz token missing")
        return token

    async def charts(self, *, market: Optional[str], limit: int) -> DiscoveryResponse:
        raise NotImplementedError

    async def tags(self, *, tag: str, limit: int) -> DiscoveryResponse:
        raise NotImplementedError

    async def new_releases(
        self, *, market: Optional[str], limit: int
    ) -> DiscoveryResponse:
        raise NotImplementedError

    async def search_albums(self, *, query: str, limit: int) -> DiscoveryResponse:
        params = {"query": query, "type": "release", "limit": str(limit)}
        headers = {"accept": "application/json"}
        try:
            headers["Authorization"] = f"Token {self.token}"
        except RuntimeError:
            pass
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(f"{self.base_url}/search", params=params, headers=headers)
        resp.raise_for_status()
        payload = resp.json()
        results = payload.get("results", [])
        items: list[AlbumItem] = []
        for result in results[:limit]:
            title = result.get("release_name") or result.get("title") or ""
            artist = result.get("artist_name") or result.get("artist_credit_name") or ""
            if not title or not artist:
                continue
            release_mbid = result.get("release_mbid") or result.get("release_group_mbid")
            source_url = None
            if release_mbid:
                source_url = f"https://listenbrainz.org/release/{release_mbid}"
            release_date = result.get("release_date") or result.get("first_release_date")
            items.append(
                AlbumItem(
                    id=release_mbid or f"{artist}-{title}",
                    canonical_key=_canonical_key(artist, title, release_date),
                    source="listenbrainz",
                    title=title,
                    artist=artist,
                    release_date=(release_date or "").strip() or None,
                    source_url=source_url,
                )
            )
        return DiscoveryResponse(provider="listenbrainz", items=items)


def _canonical_key(artist: str, title: str, release: str | None = None) -> str:
    artist_key = _slugify(artist)
    title_key = _slugify(title)
    year = (release or "")[:4]
    return f"{artist_key}::{title_key}::{year}"


def _slugify(value: str) -> str:
    normalized = value.lower().strip()
    cleaned: list[str] = []
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
