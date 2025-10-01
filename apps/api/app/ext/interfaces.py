"""Common extension interfaces used by optional provider integrations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol, Sequence, TYPE_CHECKING

if TYPE_CHECKING:
    from app.schemas.media import EnrichedCard


@dataclass(frozen=True)
class ProviderDescriptor:
    """Describe an integration that can be surfaced to the UI."""

    slug: str
    name: str
    kind: str
    description: str | None = None
    configured: bool = False
    healthy: bool = False
    available: bool = True
    metadata: Mapping[str, Any] = field(default_factory=dict)


class ProviderRegistry(Protocol):
    """Protocol for registries that expose provider descriptors."""

    kind: str

    def all(self) -> Sequence[ProviderDescriptor]:
        """Return provider descriptors known to the registry."""

    def get(self, slug: str) -> ProviderDescriptor | None:
        """Return a provider descriptor by slug when available."""


class SearchProvider(Protocol):
    """Protocol implemented by torrent/metadata search providers."""

    slug: str
    name: str

    def descriptor(self) -> ProviderDescriptor:
        """Return a descriptor describing this provider."""

    async def search(
        self,
        query: str,
        *,
        limit: int,
        kind: str,
    ) -> tuple[list["EnrichedCard"], dict[str, Any]]:
        """Execute a search returning enriched cards and meta details."""
