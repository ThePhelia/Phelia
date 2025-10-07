"""Metadata enrichment router orchestrating provider lookups."""

from __future__ import annotations

import asyncio
import logging
import re
import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional

from app.schemas.media import Classification, EnrichedCard, EnrichedProvider
from app.services.metadata.constants import TMDB_IMAGE_BASE
from app.services.metadata.metadata_client import MetadataClient, MetadataProxyError


logger = logging.getLogger(__name__)


@dataclass
class TTLCache:
    ttl: float
    maxsize: int
    data: Dict[Any, tuple[float, Any]]

    def __init__(self, ttl: float = 900.0, maxsize: int = 256) -> None:
        self.ttl = ttl
        self.maxsize = maxsize
        self.data = {}

    def get(self, key: Any) -> Any | None:
        entry = self.data.get(key)
        if not entry:
            return None
        ts, value = entry
        if time.monotonic() - ts > self.ttl:
            self.data.pop(key, None)
            return None
        return value

    def set(self, key: Any, value: Any) -> None:
        if len(self.data) >= self.maxsize:
            oldest_key = min(self.data.items(), key=lambda item: item[1][0])[0]
            self.data.pop(oldest_key, None)
        self.data[key] = (time.monotonic(), value)


class MetadataRouter:
    """Route classified titles to relevant metadata providers."""

    def __init__(
        self,
        *,
        metadata_client: "MetadataClient",
        omdb_client: Any | None,
        musicbrainz_client: Any | None,
        discogs_client: Any | None,
        threshold_low: float = 0.55,
    ) -> None:
        self.metadata = metadata_client
        self.omdb = omdb_client
        self.musicbrainz = musicbrainz_client
        self.discogs = discogs_client
        self.threshold_low = threshold_low
        self.cache = TTLCache()

    async def enrich(self, classification: Classification, title: str) -> EnrichedCard:
        """Return an :class:`EnrichedCard` for ``title``."""

        cache_key = (classification.type, title.lower())
        cached = self.cache.get(cache_key)
        if cached is not None:
            logger.debug("metadata cache hit for %s", cache_key)
            return cached.model_copy(deep=True)

        if classification.type == "music":
            card = await self._enrich_music(classification, title)
        elif classification.type == "movie":
            card = await self._enrich_video(classification, title, media_type="movie")
        elif classification.type == "tv":
            card = await self._enrich_video(classification, title, media_type="tv")
        else:
            card = self._build_base_card(classification, title)
            card.providers = []
            card.details["message"] = "No metadata providers available for this type"

        self.cache.set(cache_key, card.model_copy(deep=True))
        return card

    def _build_base_card(self, classification: Classification, title: str) -> EnrichedCard:
        return EnrichedCard(
            media_type=classification.type,
            confidence=classification.confidence,
            title=title,
            ids={},
            details={},
            providers=[],
            reasons=list(classification.reasons),
            needs_confirmation=classification.confidence < self.threshold_low,
        )

    async def _enrich_music(self, classification: Classification, title: str) -> EnrichedCard:
        card = self._build_base_card(classification, title)
        providers = {
            "MusicBrainz": EnrichedProvider(name="MusicBrainz", used=False),
            "Discogs": EnrichedProvider(name="Discogs", used=False),
            "Last.fm": EnrichedProvider(name="Last.fm", used=False),
        }

        artist = None
        album = title
        year = None
        match = re.search(r"^(?P<artist>.+?)\s+-\s+(?P<album>.+?)(?:\s*\((?P<year>\d{4})\))?(?:\s|$)", title)
        if match:
            artist = match.group("artist").strip()
            album = match.group("album").strip()
            if match.group("year"):
                try:
                    year = int(match.group("year"))
                except ValueError:
                    year = None
            card.parsed = {"artist": artist, "album": album}
            if year:
                card.parsed["year"] = year

        mb_data: dict[str, Any] | None = None
        if self.musicbrainz and hasattr(self.musicbrainz, "lookup_release_group"):
            try:
                mb_data = await self.musicbrainz.lookup_release_group(artist, album, year)
            except Exception as exc:
                logger.warning("musicbrainz lookup failed for title=%s: %s", title, exc)
                providers["MusicBrainz"].extra = {"error": str(exc)}
            else:
                if mb_data:
                    providers["MusicBrainz"].used = True
        else:
            providers["MusicBrainz"].extra = {"error": "not_configured"}

        lastfm_data: dict[str, Any] | None = None
        lastfm_error: str | None = None
        if album:
            lastfm_data, lastfm_error = await self._lastfm_album_info(artist, album)
        else:
            lastfm_error = "no_album"

        if lastfm_error:
            providers["Last.fm"].extra = {"error": lastfm_error}
        elif lastfm_data:
            providers["Last.fm"].used = True

        discogs_configured = (
            self.discogs
            and getattr(self.discogs, "token", None)
            and hasattr(self.discogs, "lookup_release")
        )
        if not discogs_configured:
            providers["Discogs"].extra = {"error": "not_configured"}

        discogs_data: dict[str, Any] | None = None
        if discogs_configured:
            mb_release_group_id = None
            if mb_data:
                release_group = mb_data.get("release_group") or {}
                mb_release_group_id = release_group.get("id")
            try:
                discogs_data = await self.discogs.lookup_release(
                    artist, album, year, mb_release_group_id
                )
            except Exception as exc:  # pragma: no cover - defensive guard
                logger.warning(
                    "provider Discogs failed for title=%s artist=%s album=%s: %s",
                    title,
                    artist,
                    album,
                    exc,
                )
                providers["Discogs"].extra = {"error": str(exc)}
            else:
                if not discogs_data and providers["Discogs"].extra is None:
                    providers["Discogs"].extra = {"error": "no_result"}

        if mb_data:
            providers["MusicBrainz"].extra = {"id": (mb_data.get("release_group") or {}).get("id")}
            artist_info = mb_data.get("artist") or {}
            release_group = mb_data.get("release_group") or {}
            if artist_info.get("id"):
                card.ids["mb_artist_id"] = artist_info.get("id")
            if release_group.get("id"):
                card.ids["mb_release_group_id"] = release_group.get("id")
            if release_group.get("first_release_date") and "year" not in (card.parsed or {}):
                try:
                    card.parsed = card.parsed or {}
                    card.parsed["year"] = int(release_group["first_release_date"][:4])
                except Exception:
                    pass
            musicbrainz_details = card.details.setdefault("musicbrainz", {})
            for key, value in mb_data.items():
                existing_value = musicbrainz_details.get(key)
                if isinstance(existing_value, dict) and isinstance(value, dict):
                    existing_value.update(value)
                else:
                    musicbrainz_details[key] = value

        if discogs_data:
            providers["Discogs"].used = True
            providers["Discogs"].extra = {"id": discogs_data.get("id")}
            card.details.setdefault("discogs", {}).update(discogs_data)
            if discogs_data.get("cover_image"):
                card.details.setdefault("images", {})["primary"] = discogs_data["cover_image"]

        if lastfm_data:
            providers["Last.fm"].extra = {"url": lastfm_data.get("url")}
            card.details.setdefault("lastfm", {}).update(lastfm_data)
            tags = lastfm_data.get("tags")
            if tags:
                card.details.setdefault("tags", list(tags))

        card.providers = list(providers.values())
        if card.parsed is None and (artist or album):
            card.parsed = {"artist": artist, "album": album}
        return card

    async def _lastfm_album_info(
        self, artist: str | None, album: str
    ) -> tuple[dict[str, Any] | None, str | None]:
        params: dict[str, Any] = {"album": album}
        if artist:
            params["artist"] = artist
        try:
            response = await self.metadata.lastfm(
                "album.getinfo", params=params, request_id=None
            )
        except MetadataProxyError as exc:
            detail = exc.detail or "lastfm_error"
            if (
                exc.status_code in {502, 503}
                and isinstance(detail, str)
                and detail == "lastfm_not_configured"
            ):
                return None, "not_configured"
            return None, str(detail) if isinstance(detail, str) else "lastfm_error"

        if not isinstance(response, dict):
            return None, "invalid_response"

        album_data = response.get("album")
        if not isinstance(album_data, dict):
            return None, "no_result"

        tags_container = album_data.get("tags") or {}
        tag_entries = tags_container.get("tag") if isinstance(tags_container, dict) else None
        tag_list: list[str] = []
        if isinstance(tag_entries, Iterable):
            for entry in tag_entries:
                if isinstance(entry, dict) and entry.get("name"):
                    tag_list.append(str(entry["name"]))

        wiki = album_data.get("wiki")
        if not isinstance(wiki, dict):
            wiki = {}

        def _to_int(value: Any) -> int | None:
            try:
                return int(value) if value is not None else None
            except (TypeError, ValueError):
                return None

        payload = {
            "tags": tag_list,
            "listeners": _to_int(album_data.get("listeners")),
            "playcount": _to_int(album_data.get("playcount")),
            "summary": wiki.get("summary"),
            "url": album_data.get("url"),
            "extra": album_data,
        }
        images = album_data.get("image")
        if isinstance(images, Iterable):
            poster = None
            for entry in images:
                if isinstance(entry, dict) and entry.get("#text"):
                    poster = entry.get("#text")
            if poster:
                payload["image"] = poster
        return payload, None

    async def _tmdb_lookup(
        self, media_type: str, title: str, year: int | None
    ) -> tuple[dict[str, Any] | None, str | None]:
        params: dict[str, Any] = {
            "query": title,
            "include_adult": False,
            "language": "en-US",
            "page": 1,
        }
        if year is not None:
            key = "year" if media_type == "movie" else "first_air_date_year"
            params[key] = year
        try:
            search = await self.metadata.tmdb(
                f"search/{media_type}", params=params, request_id=None
            )
        except MetadataProxyError as exc:
            detail = exc.detail or "tmdb_error"
            if (
                exc.status_code in {502, 503}
                and isinstance(detail, str)
                and detail == "tmdb_not_configured"
            ):
                return None, "not_configured"
            return None, str(detail) if isinstance(detail, str) else "tmdb_error"

        if not isinstance(search, dict):
            return None, "invalid_response"

        results = search.get("results")
        if not isinstance(results, list):
            return None, "invalid_response"

        primary: dict[str, Any] | None = None
        for entry in results:
            if isinstance(entry, dict):
                primary = entry
                break
        if not primary:
            return None, "no_result"

        tmdb_id = primary.get("id")
        if tmdb_id is None:
            return None, "no_result"

        try:
            details = await self.metadata.tmdb(
                f"{media_type}/{tmdb_id}",
                params={
                    "language": "en-US",
                    "append_to_response": "external_ids,credits,recommendations,similar",
                },
                request_id=None,
            )
        except MetadataProxyError as exc:
            detail = exc.detail or "tmdb_error"
            return None, str(detail) if isinstance(detail, str) else "tmdb_error"

        if not isinstance(details, dict):
            return None, "invalid_response"

        external = details.get("external_ids")
        imdb_id = external.get("imdb_id") if isinstance(external, dict) else None
        date_key = "release_date" if media_type == "movie" else "first_air_date"
        release_date = details.get(date_key) or primary.get(date_key)
        year_value = None
        if isinstance(release_date, str) and len(release_date) >= 4:
            try:
                year_value = int(release_date[:4])
            except ValueError:
                year_value = None
        poster = details.get("poster_path") or primary.get("poster_path")
        backdrop = details.get("backdrop_path") or primary.get("backdrop_path")
        overview = details.get("overview") or primary.get("overview")
        title_key = "title" if media_type == "movie" else "name"
        resolved_title = (
            details.get(title_key)
            or primary.get(title_key)
            or (details.get("name") if media_type == "movie" else details.get("title"))
            or title
        )
        payload = {
            "tmdb_id": tmdb_id,
            "title": resolved_title,
            "year": year_value,
            "overview": overview,
            "poster": f"{TMDB_IMAGE_BASE}{poster}" if poster else None,
            "backdrop": f"{TMDB_IMAGE_BASE}{backdrop}" if backdrop else None,
            "imdb_id": imdb_id,
            "extra": {"tmdb": details},
        }
        return payload, None

    async def _enrich_video(
        self,
        classification: Classification,
        title: str,
        *,
        media_type: str,
    ) -> EnrichedCard:
        card = self._build_base_card(classification, title)
        providers = {
            "TMDb": EnrichedProvider(name="TMDb", used=False),
            "OMDb": EnrichedProvider(name="OMDb", used=False),
        }

        year = None
        match = re.search(r"(19|20)\d{2}", title)
        if match:
            try:
                year = int(match.group())
            except ValueError:
                year = None
        season = None
        episode = None
        season_match = re.search(r"S(?P<season>\d{1,2})E(?P<episode>\d{1,2})", title, re.I)
        if season_match:
            try:
                season = int(season_match.group("season"))
                episode = int(season_match.group("episode"))
            except ValueError:
                season = episode = None
        elif media_type == "tv":
            season_match = re.search(r"Season\s+(?P<season>\d+)", title, re.I)
            if season_match:
                try:
                    season = int(season_match.group("season"))
                except ValueError:
                    season = None

        if season is not None:
            card.parsed = {"season": season}
            if episode is not None:
                card.parsed["episode"] = episode
        if year is not None:
            card.parsed = card.parsed or {}
            card.parsed.setdefault("year", year)

        tmdb_data, tmdb_error = await self._tmdb_lookup(media_type, title, year)

        if tmdb_data:
            providers["TMDb"].used = True
            card.ids["tmdb_id"] = tmdb_data.get("tmdb_id")
            if tmdb_data.get("imdb_id"):
                card.ids["imdb_id"] = tmdb_data["imdb_id"]
            card.details.setdefault("tmdb", {}).update(tmdb_data)
            if tmdb_data.get("poster"):
                card.details.setdefault("images", {})["poster"] = tmdb_data["poster"]
            if tmdb_data.get("backdrop"):
                card.details.setdefault("images", {})["backdrop"] = tmdb_data["backdrop"]
            card.title = tmdb_data.get("title") or card.title
            card.parsed = card.parsed or {}
            if tmdb_data.get("year"):
                card.parsed.setdefault("year", tmdb_data["year"])
        else:
            providers["TMDb"].extra = {"error": tmdb_error or "no_result"}
            if classification.type in {"movie", "tv"}:
                card.reasons.append("tmdb_missing")

        omdb_lookup = getattr(self.omdb, "fetch_by_imdb", None) if self.omdb else None
        if omdb_lookup:
            imdb_id = card.ids.get("imdb_id")
            if imdb_id:
                omdb_data = await omdb_lookup(imdb_id)
                if omdb_data:
                    providers["OMDb"].used = True
                    card.details.setdefault("omdb", {}).update(omdb_data)
                else:
                    providers["OMDb"].extra = {"error": "no_result"}
            else:
                providers["OMDb"].extra = {"error": "no_imdb_id"}
        else:
            providers["OMDb"].extra = {"error": "not_configured"}

        card.providers = list(providers.values())
        if not providers["TMDb"].used:
            card.needs_confirmation = True
            card.reasons.append("tmdb_unavailable")
        return card


__all__ = ["MetadataRouter"]

