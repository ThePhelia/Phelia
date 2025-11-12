"""Thin async wrapper around the OMDb API."""

from __future__ import annotations

import logging
from typing import Any, Callable

import httpx


logger = logging.getLogger(__name__)


class OMDbClient:
    base_url = "https://www.omdbapi.com/"

    def __init__(
        self, api_key: str | Callable[[], str | None] | None, timeout: float = 6.0
    ) -> None:
        if callable(api_key):
            self._api_key_getter: Callable[[], str | None] = api_key
            self._static_api_key: str | None = None
        else:
            self._static_api_key = api_key
            self._api_key_getter = lambda: self._static_api_key
        self.timeout = timeout

    async def fetch_by_imdb(self, imdb_id: str) -> dict[str, Any] | None:
        api_key = self.api_key
        if not api_key:
            logger.debug("omdb: missing API key, skipping lookup for %s", imdb_id)
            return None
        params = {"apikey": api_key, "i": imdb_id, "plot": "short"}
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(self.base_url, params=params)
                resp.raise_for_status()
                data = resp.json()
                if not isinstance(data, dict):
                    return None
                if data.get("Response") == "False":
                    return None
                return data
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "omdb http error imdb_id=%s status=%s",
                imdb_id,
                exc.response.status_code,
            )
        except httpx.RequestError as exc:
            logger.warning("omdb request error imdb_id=%s error=%s", imdb_id, exc)
        return None

    @property
    def api_key(self) -> str | None:
        return self._api_key_getter()


__all__ = ["OMDbClient"]
