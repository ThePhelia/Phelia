"""Thin adapter around the core qBittorrent client."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from app.services.bt.qbittorrent import QbClient

from .settings import PluginSettings


class TorrentClientAdapter:
    """Create authenticated qBittorrent client sessions based on plugin settings."""

    def __init__(self, settings: PluginSettings) -> None:
        self._settings = settings

    def build(self) -> QbClient:
        return QbClient(
            self._settings.qbittorrent_url,
            self._settings.qbittorrent_username,
            self._settings.qbittorrent_password,
        )

    @asynccontextmanager
    async def session(self) -> AsyncIterator[QbClient]:
        client = self.build()
        try:
            await client.login()
            yield client
        finally:
            await client.close()


__all__ = ["TorrentClientAdapter"]
