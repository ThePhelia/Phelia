from __future__ import annotations

import os
from typing import Optional

from ..models import DiscoveryResponse
from .base import Provider


class ListenBrainzProvider(Provider):
    name = "listenbrainz"

    def __init__(self) -> None:
        enabled = os.getenv("LISTENBRAINZ_ENABLED", "false").lower() == "true"
        token = os.getenv("LISTENBRAINZ_TOKEN")
        if not enabled or not token:
            raise RuntimeError("ListenBrainz disabled")
        self.token = token

    async def charts(self, *, market: Optional[str], limit: int) -> DiscoveryResponse:
        raise NotImplementedError

    async def tags(self, *, tag: str, limit: int) -> DiscoveryResponse:
        raise NotImplementedError

    async def new_releases(self, *, market: Optional[str], limit: int) -> DiscoveryResponse:
        raise NotImplementedError

    async def search_albums(self, *, query: str, limit: int) -> DiscoveryResponse:
        raise NotImplementedError
