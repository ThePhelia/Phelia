"""HTTP client for the internal metadata proxy service."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

import httpx

from app.core.config import settings


class MetadataProxyError(Exception):
    """Raised when the metadata proxy returns an error payload."""

    def __init__(self, status_code: int, detail: Any) -> None:
        super().__init__(f"metadata proxy error: {status_code}")
        self.status_code = status_code
        self.detail = detail


class MetadataClient:
    """Lightweight async client for the metadata proxy."""

    def __init__(self, base_url: str, *, timeout: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self._timeout = httpx.Timeout(timeout, connect=3.0, read=timeout, write=timeout)
        self._limits = httpx.Limits(max_connections=10, max_keepalive_connections=5)

    async def _get(
        self,
        provider: str,
        path: str,
        params: dict[str, Any] | None,
        request_id: str | None,
    ) -> Any:
        url = f"{self.base_url}/{provider}/{path.lstrip('/')}"
        headers = {"accept": "application/json"}
        if request_id:
            headers["x-request-id"] = request_id
        async with httpx.AsyncClient(
            timeout=self._timeout, limits=self._limits
        ) as client:
            response = await client.get(url, params=params or {}, headers=headers)
        if response.status_code >= 400:
            detail = self._extract_error(response)
            raise MetadataProxyError(response.status_code, detail)
        return response.json()

    @staticmethod
    def _extract_error(response: httpx.Response) -> Any:
        try:
            payload = response.json()
        except ValueError:  # pragma: no cover - defensive
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
        return await self._get("tmdb", path, params, request_id)

    async def lastfm(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        *,
        request_id: str | None = None,
    ) -> Any:
        payload = dict(params or {})
        if path and "method" not in payload:
            payload["method"] = path
        return await self._get("lastfm", "", payload, request_id)

    async def mb(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        *,
        request_id: str | None = None,
    ) -> Any:
        return await self._get("mb", path, params, request_id)

    async def fanart(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        *,
        request_id: str | None = None,
    ) -> Any:
        return await self._get("fanart", path, params, request_id)


@lru_cache
def get_metadata_client() -> MetadataClient:
    if not settings.METADATA_BASE_URL:
        raise RuntimeError("METADATA_BASE_URL is not configured")
    return MetadataClient(str(settings.METADATA_BASE_URL))
