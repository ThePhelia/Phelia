"""Provider HTTP clients for metadata lookups."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

import httpx

from app.core.runtime_integration_settings import runtime_integration_settings


class MetadataProxyError(Exception):
    """Raised when an upstream metadata provider returns an error payload."""

    def __init__(self, status_code: int, detail: Any) -> None:
        super().__init__(f"metadata upstream error: {status_code}")
        self.status_code = status_code
        self.detail = detail


class MetadataClient:
    """Lightweight async client for third-party metadata providers."""

    tmdb_base_url = "https://api.themoviedb.org/3"
    lastfm_base_url = "https://ws.audioscrobbler.com/2.0/"
    musicbrainz_base_url = "https://musicbrainz.org/ws/2"
    fanart_base_url = "https://webservice.fanart.tv/v3"

    def __init__(self, *, timeout: float = 10.0) -> None:
        self._timeout = httpx.Timeout(timeout, connect=3.0, read=timeout, write=timeout)
        self._limits = httpx.Limits(max_connections=10, max_keepalive_connections=5)

    async def _request(
        self,
        base_url: str,
        path: str,
        *,
        params: dict[str, Any] | None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
        req_headers = {"accept": "application/json"}
        if headers:
            req_headers.update(headers)
        async with httpx.AsyncClient(timeout=self._timeout, limits=self._limits) as client:
            response = await client.get(url, params=params or {}, headers=req_headers)
        if response.status_code >= 400:
            raise MetadataProxyError(response.status_code, self._extract_error(response))
        return response.json()

    @staticmethod
    def _extract_error(response: httpx.Response) -> Any:
        try:
            payload = response.json()
        except ValueError:  # pragma: no cover
            payload = response.text
        if isinstance(payload, dict) and "detail" in payload:
            return payload["detail"]
        return payload

    async def tmdb(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        *,
        request_id: str | None = None,
    ) -> Any:
        api_key = runtime_integration_settings.get("tmdb.api_key")
        if not api_key:
            raise MetadataProxyError(503, "tmdb_api_key_missing")
        payload = dict(params or {})
        payload["api_key"] = api_key
        headers = {"accept": "application/json"}
        if request_id:
            headers["x-request-id"] = request_id
        return await self._request(self.tmdb_base_url, path, params=payload, headers=headers)

    async def lastfm(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        *,
        request_id: str | None = None,
    ) -> Any:
        api_key = runtime_integration_settings.get("lastfm.api_key")
        if not api_key:
            raise MetadataProxyError(503, "lastfm_api_key_missing")
        payload = dict(params or {})
        payload.setdefault("method", path)
        payload["api_key"] = api_key
        payload["format"] = "json"
        headers = {"accept": "application/json"}
        if request_id:
            headers["x-request-id"] = request_id
        return await self._request(self.lastfm_base_url, "", params=payload, headers=headers)

    async def mb(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        *,
        request_id: str | None = None,
    ) -> Any:
        payload = dict(params or {})
        payload.setdefault("fmt", "json")
        headers = {
            "accept": "application/json",
            "User-Agent": runtime_integration_settings.get("musicbrainz.user_agent")
            or "Phelia/0.1 (https://example.local)",
        }
        if request_id:
            headers["x-request-id"] = request_id
        return await self._request(self.musicbrainz_base_url, path, params=payload, headers=headers)

    async def fanart(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        *,
        request_id: str | None = None,
    ) -> Any:
        api_key = runtime_integration_settings.get("fanart.api_key")
        if not api_key:
            raise MetadataProxyError(503, "fanart_api_key_missing")
        headers = {"api-key": api_key}
        if request_id:
            headers["x-request-id"] = request_id
        return await self._request(self.fanart_base_url, path, params=params, headers=headers)


@lru_cache
def get_metadata_client() -> MetadataClient:
    return MetadataClient()
