"""Registry for torrent/metadata search providers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Sequence

from app.ext.interfaces import ProviderDescriptor, ProviderRegistry, SearchProvider


@dataclass
class _NullSearchProvider(SearchProvider):
    slug: str = "_none"
    name: str = "Torrent search unavailable"
    description: str = "No torrent providers are currently installed."

    def descriptor(self) -> ProviderDescriptor:
        return ProviderDescriptor(
            slug=self.slug,
            name=self.name,
            kind="search",
            description=self.description,
            configured=False,
            healthy=False,
            available=False,
            metadata={"message": self.description},
        )

    async def search(
        self,
        query: str,
        *,
        limit: int,
        kind: str,
    ) -> tuple[list["EnrichedCard"], dict[str, str]]:
        from app.schemas.media import EnrichedCard  # local import to avoid cycle

        _ = (query, limit, kind)  # unused in the fallback provider
        return [], {"message": self.description}


@dataclass
class SearchProviderRegistry(ProviderRegistry):
    """Keep track of search providers configured for the application."""

    kind: str = "search"
    _providers: Dict[str, SearchProvider] = field(default_factory=dict)
    _fallback: _NullSearchProvider = field(default_factory=_NullSearchProvider)

    def register(self, provider: SearchProvider) -> None:
        self._providers[provider.slug] = provider

    def unregister(self, slug: str) -> None:
        self._providers.pop(slug, None)

    def all(self) -> Sequence[ProviderDescriptor]:
        if not self._providers:
            return [self._fallback.descriptor()]
        return [provider.descriptor() for provider in self._providers.values()]

    def get(self, slug: str) -> ProviderDescriptor | None:
        provider = self._providers.get(slug)
        if provider is None:
            if slug == self._fallback.slug:
                return self._fallback.descriptor()
            return None
        return provider.descriptor()

    def primary(self) -> SearchProvider:
        return next(iter(self._providers.values()), self._fallback)

    def is_configured(self) -> bool:
        return any(descriptor.configured for descriptor in self.all())


search_registry = SearchProviderRegistry()

__all__ = ["SearchProviderRegistry", "search_registry"]
