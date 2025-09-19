"""Metadata enrichment router orchestrating provider lookups."""

from __future__ import annotations

import asyncio
import logging
import re
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

from app.schemas.media import Classification, EnrichedCard, EnrichedProvider


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
        tmdb_client: Any | None,
        omdb_client: Any | None,
        musicbrainz_client: Any | None,
        discogs_client: Any | None,
        lastfm_client: Any | None,
        threshold_low: float = 0.55,
    ) -> None:
        self.tmdb = tmdb_client
        self.omdb = omdb_client
        self.musicbrainz = musicbrainz_client
        self.discogs = discogs_client
        self.lastfm = lastfm_client
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

        tasks: dict[str, asyncio.Task[Any]] = {}
        if self.musicbrainz and hasattr(self.musicbrainz, "lookup_release_group"):
            tasks["MusicBrainz"] = asyncio.create_task(
                self.musicbrainz.lookup_release_group(artist, album, year)
            )
        if self.discogs and getattr(self.discogs, "token", None) and hasattr(self.discogs, "lookup_release"):
            tasks["Discogs"] = asyncio.create_task(
                self.discogs.lookup_release(artist, album, year, None)
            )
        else:
            providers["Discogs"].extra = {"error": "not_configured"}
        if self.lastfm and getattr(self.lastfm, "api_key", None) and hasattr(self.lastfm, "get_album_info"):
            tasks["Last.fm"] = asyncio.create_task(self.lastfm.get_album_info(artist, album))
        else:
            providers["Last.fm"].extra = {"error": "not_configured"}

        results: dict[str, Any] = {}
        if tasks:
            gathered = await asyncio.gather(*tasks.values(), return_exceptions=True)
            for name, result in zip(tasks.keys(), gathered, strict=False):
                if isinstance(result, Exception):
                    logger.warning("provider %s failed for title=%s: %s", name, title, result)
                    providers[name].extra = {"error": str(result)}
                    continue
                results[name] = result

        mb_data = results.get("MusicBrainz")
        if mb_data:
            providers["MusicBrainz"].used = True
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
            card.details.setdefault("musicbrainz", release_group)

        discogs_data = results.get("Discogs")
        if discogs_data:
            providers["Discogs"].used = True
            providers["Discogs"].extra = {"id": discogs_data.get("id")}
            card.details.setdefault("discogs", {}).update(discogs_data)
            if discogs_data.get("cover_image"):
                card.details.setdefault("images", {})["primary"] = discogs_data["cover_image"]

        lastfm_data = results.get("Last.fm")
        if lastfm_data:
            providers["Last.fm"].used = True
            providers["Last.fm"].extra = {"url": lastfm_data.get("url")}
            card.details.setdefault("lastfm", {}).update(lastfm_data)
            tags = lastfm_data.get("tags")
            if tags:
                card.details.setdefault("tags", list(tags))

        card.providers = list(providers.values())
        if card.parsed is None and (artist or album):
            card.parsed = {"artist": artist, "album": album}
        return card

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

        tmdb_data: Optional[dict[str, Any]] = None
        if self.tmdb and hasattr(self.tmdb, "movie_lookup") and media_type == "movie":
            tmdb_data = await self.tmdb.movie_lookup(title, year)
        elif self.tmdb and hasattr(self.tmdb, "tv_lookup") and media_type == "tv":
            tmdb_data = await self.tmdb.tv_lookup(title, year)
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
            providers["TMDb"].extra = {"error": "no_result"}
            if classification.type in {"movie", "tv"}:
                card.reasons.append("tmdb_missing")

        if self.omdb and card.ids.get("imdb_id") and hasattr(self.omdb, "fetch_by_imdb"):
            omdb_data = await self.omdb.fetch_by_imdb(card.ids["imdb_id"])
            if omdb_data:
                providers["OMDb"].used = True
                card.details.setdefault("omdb", {}).update(omdb_data)
            else:
                providers["OMDb"].extra = {"error": "no_result"}
        else:
            providers["OMDb"].extra = {"error": "not_configured"}

        card.providers = list(providers.values())
        if not providers["TMDb"].used:
            card.needs_confirmation = True
            card.reasons.append("tmdb_unavailable")
        return card


__all__ = ["MetadataRouter"]

