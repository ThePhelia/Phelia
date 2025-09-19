"""Thin async wrapper around the OMDb API."""

from __future__ import annotations

import logging
from typing import Any

import httpx


logger = logging.getLogger(__name__)


class OMDbClient:
    base_url = "https://www.omdbapi.com/"

    def __init__(self, api_key: str | None, timeout: float = 6.0) -> None:
        self.api_key = api_key
        self.timeout = timeout

    async def fetch_by_imdb(self, imdb_id: str) -> dict[str, Any] | None:
        if not self.api_key:
            logger.debug("omdb: missing API key, skipping lookup for %s", imdb_id)
            return None
        params = {"apikey": self.api_key, "i": imdb_id, "plot": "short"}
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
            logger.warning("omdb http error imdb_id=%s status=%s", imdb_id, exc.response.status_code)
        except httpx.RequestError as exc:
            logger.warning("omdb request error imdb_id=%s error=%s", imdb_id, exc)
        return None


__all__ = ["OMDbClient"]

