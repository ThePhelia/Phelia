"""Search provider implementation backed by Jackett Torznab."""

from __future__ import annotations

import logging
from typing import Any, Iterable, Sequence

import httpx

from app.ext.interfaces import ProviderDescriptor, SearchProvider
from app.schemas.media import EnrichedCard, EnrichedProvider
from app.services.metadata.classifier import Classifier

from .normalizer import NormalizedResult, parse_torznab
from .qbit_client import TorrentClientAdapter
from .settings import PluginSettings


class JackettProvider(SearchProvider):
    """Jackett-backed torrent search provider."""

    slug = "jackett"
    name = "Jackett Torznab"

    def __init__(
        self,
        settings: PluginSettings,
        logger: logging.Logger | None = None,
        timeout: float = 20.0,
    ) -> None:
        self._logger = logger or logging.getLogger(__name__)
        self._settings = settings
        self._timeout = timeout
        self._classifier = Classifier()
        self._torrent_client = TorrentClientAdapter(settings)
        self._last_health: str | None = None

    @property
    def settings(self) -> PluginSettings:
        return self._settings

    def update_settings(self, settings: PluginSettings) -> None:
        self._settings = settings
        self._torrent_client = TorrentClientAdapter(settings)

    def descriptor(self) -> ProviderDescriptor:
        configured = bool(
            self._settings.jackett_api_key
            and self._settings.qbittorrent_username
            and self._settings.qbittorrent_password
        )
        healthy = self._last_health == "ok"
        return ProviderDescriptor(
            slug=self.slug,
            name=self.name,
            kind="search",
            description="Search Jackett and enqueue torrents to qBittorrent.",
            configured=configured,
            healthy=healthy,
            available=True,
            metadata={
                "jackett_url": self._settings.jackett_url,
                "qbittorrent_url": self._settings.qbittorrent_url,
            },
        )

    async def search(
        self,
        query: str,
        *,
        limit: int,
        kind: str,
    ) -> tuple[list[EnrichedCard], dict[str, Any]]:
        _ = kind  # currently unused; search delegates query directly
        api_key = self._settings.jackett_api_key
        if not api_key:
            raise RuntimeError("Jackett API key is not configured")

        url = f"{self._settings.jackett_url}/api/v2.0/indexers/all/results/torznab/api"
        params = {
            "apikey": api_key,
            "t": "search",
            "q": query,
        }
        if self._settings.category_filters:
            params["cat"] = ",".join(self._settings.category_filters)
        if limit:
            params["limit"] = str(limit)

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(url, params=params)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            self._last_health = "error"
            self._logger.error("Jackett search failed for %s: %s", query, exc)
            raise

        payload = response.text

        results = parse_torznab(payload)
        filtered = self._filter_results(results)

        cards: list[EnrichedCard] = []
        for result in filtered[:limit]:
            card = self._to_enriched_card(result)
            cards.append(card)

        self._last_health = "ok"
        meta = {
            "count": len(cards),
            "query": query,
            "jackett": {
                "url": self._settings.jackett_url,
                "filtered": len(results) - len(filtered),
            },
        }
        return cards, meta

    def _filter_results(
        self, results: Sequence[NormalizedResult]
    ) -> list[NormalizedResult]:
        allow = {
            entry.lower()
            for entry in (self._settings.allowlist or [])
            if isinstance(entry, str) and entry.strip()
        }
        block = {
            entry.lower()
            for entry in (self._settings.blocklist or [])
            if isinstance(entry, str) and entry.strip()
        }
        minimum_seeders = max(0, self._settings.minimum_seeders)

        filtered: list[NormalizedResult] = []
        for result in results:
            tracker_name = (result.tracker or "").lower()
            if allow and tracker_name not in allow:
                continue
            if block and tracker_name in block:
                continue
            if minimum_seeders and result.seeders < minimum_seeders:
                continue
            filtered.append(result)
        return filtered

    def _to_enriched_card(self, result: NormalizedResult) -> EnrichedCard:
        classification = self._classifier.classify_torrent(
            result.title,
            category_hint=",".join(result.categories),
            indexer_name=result.tracker,
        )

        details: dict[str, Any] = {
            "jackett": {
                "tracker": result.tracker,
                "categories": list(result.categories),
                "seeders": result.seeders,
                "peers": result.peers,
                "size": result.size,
                "pubDate": result.pub_date.isoformat() if result.pub_date else None,
                "torrentUrl": result.torrent_url,
                "magnet": result.magnet,
                "attributes": dict(result.attributes),
            }
        }
        parsed = {
            "title": result.title,
            "guid": result.guid,
            "magnet": result.magnet,
            "link": result.link,
            "seeders": result.seeders,
            "peers": result.peers,
            "size": result.size,
        }
        providers = [
            EnrichedProvider(
                name=result.tracker or "Jackett",
                used=True,
                extra={"jackett": True},
            )
        ]
        card = EnrichedCard(
            media_type=classification.type,
            confidence=classification.confidence,
            title=result.title,
            parsed=parsed,
            details=details,
            providers=providers,
            reasons=classification.reasons,
            needs_confirmation=classification.confidence < 0.4,
        )
        return card

    async def send_to_qbittorrent(
        self, results: Iterable[NormalizedResult]
    ) -> list[str]:
        created: list[str] = []

        async with self._torrent_client.session() as client:
            async with httpx.AsyncClient(timeout=self._timeout) as downloader:
                for result in results:
                    if result.magnet:
                        await client.add_magnet(result.magnet)
                        created.append(result.title)
                        continue
                    torrent_url = result.torrent_url or result.link
                    if not torrent_url:
                        self._logger.warning(
                            "Skipping %s: no magnet or torrent URL", result.title
                        )
                        continue
                    try:
                        resp = await downloader.get(torrent_url)
                        resp.raise_for_status()
                        await client.add_torrent_file(resp.content)
                        created.append(result.title)
                    except httpx.HTTPError as exc:
                        self._logger.error(
                            "Failed to download torrent for %s: %s", result.title, exc
                        )
        return created


__all__ = ["JackettProvider"]
