"""Discogs metadata provider (master/release search)."""

from __future__ import annotations

import logging
from typing import Any, Callable

import httpx


logger = logging.getLogger(__name__)


class DiscogsClient:
    base_url = "https://api.discogs.com"

    def __init__(
        self, token: str | Callable[[], str | None] | None, timeout: float = 8.0
    ) -> None:
        if callable(token):
            self._token_getter: Callable[[], str | None] = token
            self._static_token: str | None = None
        else:
            self._static_token = token
            self._token_getter = lambda: self._static_token
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        headers = {"User-Agent": "Phelia/0.1 (Discogs metadata)"}
        token = self.token
        if token:
            headers["Authorization"] = f"Discogs token={token}"
        return headers

    async def search_albums(
        self,
        query: str,
        *,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Return Discogs search hits for ``query``."""

        token = self.token
        if not query or not token:
            logger.debug(
                "discogs: skipping search query=%s token_present=%s", query, bool(token)
            )
            return []

        per_page = max(1, min(limit, 25))
        params: dict[str, str | int] = {
            "q": query,
            "type": "master",
            "per_page": per_page,
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(
                    f"{self.base_url}/database/search",
                    params=params,
                    headers=self._headers(),
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "discogs http error search=%s status=%s",
                query,
                exc.response.status_code,
            )
            return []
        except httpx.RequestError as exc:
            logger.warning("discogs request error search=%s error=%s", query, exc)
            return []

        if not isinstance(data, dict):
            return []
        results = data.get("results") or []
        if not isinstance(results, list):
            return []
        return results[:limit]

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
        params: dict[str, str | int] = {"type": "master", "per_page": 5}
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
                resp = await client.get(
                    f"{self.base_url}/database/search",
                    params=params,
                    headers=self._headers(),
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "discogs http error album=%s status=%s", album, exc.response.status_code
            )
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
            format_names = [
                f.get("name") if isinstance(f, dict) else f for f in formats
            ]
        else:
            format_names = [str(formats)]
        return {
            "id": best.get("id"),
            "title": best.get("title"),
            "year": best.get("year"),
            "label": (
                (best.get("label") or [None])[0]
                if isinstance(best.get("label"), list)
                else best.get("label")
            ),
            "catalog_number": best.get("catno"),
            "thumb": best.get("thumb"),
            "cover_image": best.get("cover_image"),
            "formats": [f for f in format_names if f],
            "extra": best,
        }

    async def fetch_resource(self, resource_url: str) -> dict[str, Any] | None:
        """Fetch a Discogs resource by URL."""

        if not resource_url:
            return None
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(resource_url, headers=self._headers())
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "discogs http error resource=%s status=%s",
                resource_url,
                exc.response.status_code,
            )
        except httpx.RequestError as exc:
            logger.warning(
                "discogs request error resource=%s error=%s", resource_url, exc
            )
        return None

    @property
    def token(self) -> str | None:
        return self._token_getter()


__all__ = ["DiscogsClient"]
