"""MusicBrainz client focusing on release-group discovery."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.services.metadata.metadata_client import MetadataClient, MetadataProxyError

logger = logging.getLogger(__name__)


class MusicBrainzClient:
    base_url = "https://musicbrainz.org/ws/2"

    def __init__(
        self,
        user_agent: str,
        timeout: float = 8.0,
        *,
        metadata_client: MetadataClient | None = None,
    ) -> None:
        self.user_agent = user_agent
        self.timeout = timeout
        self._metadata_client = metadata_client

    def _headers(self) -> dict[str, str]:
        return {"Accept": "application/json", "User-Agent": self.user_agent}

    async def _fetch(self, path: str, params: dict[str, str]) -> dict[str, Any] | None:
        if self._metadata_client is not None:
            try:
                data = await self._metadata_client.mb(path, params=params, request_id=None)
            except MetadataProxyError as exc:
                logger.warning("mb proxy error path=%s status=%s", path, exc.status_code)
                return None
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("mb proxy request error path=%s error=%s", path, exc)
                return None
            return data if isinstance(data, dict) else None

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(
                    f"{self.base_url.rstrip('/')}/{path.lstrip('/')}",
                    params=params,
                    headers=self._headers(),
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as exc:
            logger.warning("mb http error path=%s status=%s", path, exc.response.status_code)
            return None
        except httpx.RequestError as exc:
            logger.warning("mb request error path=%s error=%s", path, exc)
            return None
        return data if isinstance(data, dict) else None

    async def lookup_release_group(
        self,
        artist: str | None,
        album: str,
        year: int | None = None,
    ) -> dict[str, Any] | None:
        if not album:
            return None
        query_parts = [f'release:"{album}"']
        if artist:
            query_parts.append(f'artist:"{artist}"')
        if year:
            query_parts.append(f'firstreleasedate:{year}')
        params: dict[str, str] = {
            "query": " AND ".join(query_parts),
            "fmt": "json",
            "limit": "5",
        }
        data = await self._fetch("release-group", params)
        if not data:
            return None
        groups = data.get("release-groups") or []
        if not groups:
            return None
        best = groups[0]
        artist_credit = best.get("artist-credit") or []
        artist_data = artist_credit[0].get("artist") if artist_credit else None
        return {
            "artist": {
                "id": (artist_data or {}).get("id"),
                "name": (artist_data or {}).get("name"),
            },
            "release_group": {
                "id": best.get("id"),
                "title": best.get("title"),
                "first_release_date": best.get("first-release-date"),
                "primary_type": best.get("primary-type"),
            },
            "extra": data,
        }


__all__ = ["MusicBrainzClient"]
