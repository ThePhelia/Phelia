"""Client for Last.fm metadata endpoints."""

from __future__ import annotations

import logging
from typing import Any

import httpx


logger = logging.getLogger(__name__)


class LastFMClient:
    base_url = "https://ws.audioscrobbler.com/2.0/"

    def __init__(self, api_key: str | None, timeout: float = 6.0) -> None:
        self.api_key = api_key
        self.timeout = timeout

    async def get_album_info(self, artist: str | None, album: str) -> dict[str, Any] | None:
        if not self.api_key:
            logger.debug("lastfm: missing API key, skipping lookup")
            return None
        params = {
            "method": "album.getinfo",
            "api_key": self.api_key,
            "format": "json",
            "album": album,
        }
        if artist:
            params["artist"] = artist
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(self.base_url, params=params)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as exc:
            logger.warning("lastfm http error album=%s status=%s", album, exc.response.status_code)
            return None
        except httpx.RequestError as exc:
            logger.warning("lastfm request error album=%s error=%s", album, exc)
            return None

        album_data = data.get("album") if isinstance(data, dict) else None
        if not isinstance(album_data, dict):
            return None
        tags = album_data.get("tags", {}).get("tag", [])
        if isinstance(tags, list):
            tag_list = [t.get("name") for t in tags if isinstance(t, dict) and t.get("name")]
        else:
            tag_list = []
        wiki = album_data.get("wiki") or {}
        listeners = album_data.get("listeners")
        playcount = album_data.get("playcount")
        try:
            listeners_val = int(listeners) if listeners is not None else None
        except (TypeError, ValueError):
            listeners_val = None
        try:
            playcount_val = int(playcount) if playcount is not None else None
        except (TypeError, ValueError):
            playcount_val = None

        return {
            "tags": tag_list,
            "listeners": listeners_val,
            "playcount": playcount_val,
            "summary": wiki.get("summary"),
            "url": album_data.get("url"),
            "extra": album_data,
        }


__all__ = ["LastFMClient"]

