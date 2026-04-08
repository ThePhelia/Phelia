from __future__ import annotations

from collections.abc import Callable
from typing import Optional

from ..models import DiscoveryResponse
from .base import Provider


class ListenBrainzProvider(Provider):
    name = "listenbrainz"

    def __init__(self, token_getter: Callable[[], Optional[str]]) -> None:
        self._token_getter = token_getter
        if not self._token_getter():
            raise RuntimeError("ListenBrainz token missing")
        self.base_url = "https://api.listenbrainz.org/1"
        self.timeout = 8.0

    @property
    def token(self) -> str:
        token = self._token_getter()
        if not token:
            raise RuntimeError("ListenBrainz token missing")
        return token

    async def charts(self, *, market: Optional[str], limit: int) -> DiscoveryResponse:
        raise NotImplementedError

    async def tags(self, *, tag: str, limit: int) -> DiscoveryResponse:
        raise NotImplementedError

    async def new_releases(
        self, *, market: Optional[str], limit: int
    ) -> DiscoveryResponse:
        raise NotImplementedError

    async def search_albums(self, *, query: str, limit: int) -> DiscoveryResponse:  # noqa: ARG002
        raise NotImplementedError
