"""Discogs metadata provider (master/release search)."""

from __future__ import annotations

import logging
from typing import Any

import httpx


logger = logging.getLogger(__name__)


class DiscogsClient:
    base_url = "https://api.discogs.com"

    def __init__(self, token: str | None, timeout: float = 8.0) -> None:
        self.token = token
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        headers = {"User-Agent": "Phelia/0.1 (Discogs metadata)"}
        if self.token:
            headers["Authorization"] = f"Discogs token={self.token}"
        return headers

    async def lookup_release(
        self,
        artist: str | None,
        album: str,
        year: int | None = None,
        mb_release_group_id: str | None = None,
    ) -> dict[str, Any] | None:
        if not self.token:
            logger.debug("discogs: missing token, skipping lookup")
            return None
        params = {"type": "master", "per_page": 5}
        if artist:
            params["artist"] = artist
        if album:
            params["release_title"] = album
        if year:
            params["year"] = year
        if mb_release_group_id:
            params["mbid"] = mb_release_group_id
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(f"{self.base_url}/database/search", params=params, headers=self._headers())
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as exc:
            logger.warning("discogs http error album=%s status=%s", album, exc.response.status_code)
            return None
        except httpx.RequestError as exc:
            logger.warning("discogs request error album=%s error=%s", album, exc)
            return None

        if not isinstance(data, dict):
            return None
        results = data.get("results") or []
        if not results:
            return None
        best = results[0]
        formats = best.get("format") or best.get("formats") or []
        if isinstance(formats, list):
            format_names = [f.get("name") if isinstance(f, dict) else f for f in formats]
        else:
            format_names = [str(formats)]
        return {
            "id": best.get("id"),
            "title": best.get("title"),
            "year": best.get("year"),
            "label": (best.get("label") or [None])[0] if isinstance(best.get("label"), list) else best.get("label"),
            "catalog_number": best.get("catno"),
            "thumb": best.get("thumb"),
            "cover_image": best.get("cover_image"),
            "formats": [f for f in format_names if f],
            "extra": best,
        }


__all__ = ["DiscogsClient"]

