from __future__ import annotations

import asyncio
import base64
import os
import random
import time
from typing import Any, Dict, List, Optional

import httpx

from ..models import AlbumItem, DiscoveryResponse
from .base import Provider

SPOTIFY_API_ROOT = "https://api.spotify.com/v1"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
_token_cache: dict[str, tuple[str, float]] = {}


class SpotifyProvider(Provider):
    name = "spotify"

    def __init__(self) -> None:
        client_id = os.getenv("SPOTIFY_CLIENT_ID")
        client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
        enabled = os.getenv("SPOTIFY_ENABLED", "false").lower() == "true"
        if not enabled or not client_id or not client_secret:
            raise RuntimeError("Spotify disabled")
        self.client_id = client_id
        self.client_secret = client_secret
        self.timeout = float(os.getenv("DISCOVERY_HTTP_TIMEOUT", "8"))

    async def _get_token(self) -> str:
        cached = _token_cache.get(self.client_id)
        if cached and cached[1] > time.time():
            return cached[0]
        auth_header = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        data = {"grant_type": "client_credentials"}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                SPOTIFY_TOKEN_URL,
                data=data,
                headers={"Authorization": f"Basic {auth_header}"},
            )
        resp.raise_for_status()
        payload = resp.json()
        token = payload.get("access_token")
        expires_in = int(payload.get("expires_in", 3600))
        _token_cache[self.client_id] = (token, time.time() + expires_in - 60)
        return token

    async def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        token = await self._get_token()
        retries = 2
        delay = 0.5
        last_error: Exception | None = None
        for attempt in range(retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.get(
                        f"{SPOTIFY_API_ROOT}{path}",
                        params=params,
                        headers={"Authorization": f"Bearer {token}"},
                    )
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

    async def new_releases(self, *, market: Optional[str], limit: int) -> DiscoveryResponse:
        params = {"country": (market or os.getenv("DISCOVERY_DEFAULT_MARKET", "US")), "limit": limit}
        payload = await self._get("/browse/new-releases", params=params)
        albums = (payload.get("albums") or {}).get("items", [])
        items: List[AlbumItem] = []
        for album in albums[:limit]:
            artist_names = ", ".join(artist.get("name") for artist in album.get("artists", []))
            title = album.get("name") or ""
            if not artist_names or not title:
                continue
            release_date = album.get("release_date")
            market_code = params.get("country")
            items.append(
                AlbumItem(
                    id=album.get("id"),
                    canonical_key=_canonical_key(artist_names, title, release_date),
                    source="spotify",
                    title=title,
                    artist=artist_names,
                    release_date=release_date,
                    cover_url=(album.get("images") or [{}])[0].get("url"),
                    source_url=album.get("external_urls", {}).get("spotify"),
                    market=market_code,
                    score=0.6,
                )
            )
        return DiscoveryResponse(provider="spotify", items=items)

    async def search_albums(self, *, query: str, limit: int) -> DiscoveryResponse:
        raise NotImplementedError


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
