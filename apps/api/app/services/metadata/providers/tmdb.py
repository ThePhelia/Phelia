"""Async client for The Movie Database (TMDb) v3 API."""

from __future__ import annotations

import logging
from typing import Any, Literal, Tuple

import httpx


logger = logging.getLogger(__name__)

TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/original"


class TMDBClient:
    """Minimal TMDb wrapper used for movie/TV enrichment."""

    base_url = "https://api.themoviedb.org/3"

    def __init__(self, api_key: str | None, timeout: float = 8.0) -> None:
        self.api_key = api_key
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {"Accept": "application/json"}

    async def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any] | None:
        if not self.api_key:
            logger.debug("tmdb: missing API key, skipping request to %s", path)
            return None
        query = {"api_key": self.api_key, **params}
        url = f"{self.base_url}{path}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(url, params=query, headers=self._headers())
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as exc:
            logger.warning("tmdb http error path=%s status=%s", path, exc.response.status_code)
        except httpx.RequestError as exc:
            logger.warning("tmdb request error path=%s error=%s", path, exc)
        return None

    async def _search(
        self,
        media_type: Literal["movie", "tv"],
        title: str,
        year: int | None = None,
        language: str = "en-US",
    ) -> dict[str, Any] | None:
        params: dict[str, Any] = {
            "query": title,
            "include_adult": False,
            "language": language,
            "page": 1,
        }
        if year is not None:
            params["year" if media_type == "movie" else "first_air_date_year"] = year
        data = await self._get(f"/search/{media_type}", params)
        if not data:
            return None
        results = data.get("results") or []
        if not results:
            return None
        return results[0]

    async def _details(
        self,
        media_type: Literal["movie", "tv"],
        tmdb_id: int,
        language: str = "en-US",
    ) -> dict[str, Any] | None:
        params = {"language": language, "append_to_response": "external_ids"}
        return await self._get(f"/{media_type}/{tmdb_id}", params)

    async def movie_lookup(self, title: str, year: int | None = None) -> dict[str, Any] | None:
        """Return canonical movie details for ``title`` from TMDb."""

        primary = await self._search("movie", title, year=year)
        if not primary:
            return None
        tmdb_id = primary.get("id")
        if tmdb_id is None:
            return None
        details = await self._details("movie", tmdb_id)
        if not details:
            return None
        external = (details.get("external_ids") or {}) if isinstance(details, dict) else {}
        imdb_id = external.get("imdb_id") if isinstance(external, dict) else None
        release_date = details.get("release_date") or primary.get("release_date")
        year_value = None
        if isinstance(release_date, str) and len(release_date) >= 4:
            try:
                year_value = int(release_date[:4])
            except ValueError:
                year_value = None
        poster = details.get("poster_path") or primary.get("poster_path")
        backdrop = details.get("backdrop_path") or primary.get("backdrop_path")
        result = {
            "tmdb_id": tmdb_id,
            "title": details.get("title") or primary.get("title") or title,
            "year": year_value,
            "overview": details.get("overview") or primary.get("overview"),
            "poster": f"{TMDB_IMAGE_BASE}{poster}" if poster else None,
            "backdrop": f"{TMDB_IMAGE_BASE}{backdrop}" if backdrop else None,
            "imdb_id": imdb_id,
            "extra": {"tmdb": details},
        }
        return result

    async def tv_lookup(self, title: str, year: int | None = None) -> dict[str, Any] | None:
        """Return canonical TV details for ``title`` from TMDb."""

        primary = await self._search("tv", title, year=year)
        if not primary:
            return None
        tmdb_id = primary.get("id")
        if tmdb_id is None:
            return None
        details = await self._details("tv", tmdb_id)
        if not details:
            return None
        external = (details.get("external_ids") or {}) if isinstance(details, dict) else {}
        imdb_id = external.get("imdb_id") if isinstance(external, dict) else None
        first_air = details.get("first_air_date") or primary.get("first_air_date")
        year_value = None
        if isinstance(first_air, str) and len(first_air) >= 4:
            try:
                year_value = int(first_air[:4])
            except ValueError:
                year_value = None
        poster = details.get("poster_path") or primary.get("poster_path")
        backdrop = details.get("backdrop_path") or primary.get("backdrop_path")
        result = {
            "tmdb_id": tmdb_id,
            "title": details.get("name") or primary.get("name") or title,
            "year": year_value,
            "overview": details.get("overview") or primary.get("overview"),
            "poster": f"{TMDB_IMAGE_BASE}{poster}" if poster else None,
            "backdrop": f"{TMDB_IMAGE_BASE}{backdrop}" if backdrop else None,
            "imdb_id": imdb_id,
            "extra": {"tmdb": details},
        }
        return result


    async def discover_media(
        self,
        media_type: Literal["movie", "tv"],
        sort: str = "trending",
        page: int = 1,
        language: str = "en-US",
    ) -> dict[str, Any] | None:
        """Return paginated discovery results for the requested ``media_type``."""

        if page < 1:
            page = 1
        path, params = self._discovery_request(media_type, sort, page, language)
        return await self._get(path, params)

    def _discovery_request(
        self,
        media_type: Literal["movie", "tv"],
        sort: str,
        page: int,
        language: str,
    ) -> Tuple[str, dict[str, Any]]:
        normalized = (sort or "trending").lower()
        params: dict[str, Any] = {"page": page, "language": language}
        if normalized == "popular":
            path = f"/{media_type}/popular"
        elif normalized == "new":
            path = "/movie/now_playing" if media_type == "movie" else "/tv/on_the_air"
        elif normalized == "az":
            path = f"/discover/{media_type}"
            params.update(
                {
                    "sort_by": "original_title.asc"
                    if media_type == "movie"
                    else "name.asc",
                    "include_adult": False,
                }
            )
        else:
            # Default to trending over the past week which aligns best with discovery UI expectations.
            path = f"/trending/{media_type}/week"
        return path, params


__all__ = ["TMDBClient"]

