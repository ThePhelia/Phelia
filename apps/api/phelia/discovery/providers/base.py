from __future__ import annotations

import abc
from typing import List, Optional

from ..models import AlbumItem, DiscoveryResponse


class Provider(abc.ABC):
    name: str

    @abc.abstractmethod
    async def charts(self, *, market: Optional[str], limit: int) -> DiscoveryResponse:
        raise NotImplementedError

    @abc.abstractmethod
    async def tags(self, *, tag: str, limit: int) -> DiscoveryResponse:
        raise NotImplementedError

    @abc.abstractmethod
    async def new_releases(self, *, market: Optional[str], limit: int) -> DiscoveryResponse:
        raise NotImplementedError

    @abc.abstractmethod
    async def search_albums(self, *, query: str, limit: int) -> DiscoveryResponse:
        raise NotImplementedError
