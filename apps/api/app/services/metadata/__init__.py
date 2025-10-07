"""Factory helpers for metadata classification and enrichment."""

from __future__ import annotations

from functools import lru_cache

from app.core.config import settings
from app.core.runtime_settings import runtime_settings

from .classifier import Classifier
from .metadata_client import MetadataClient, get_metadata_client
from .router import MetadataRouter
from .providers.omdb import OMDbClient
from .providers.musicbrainz import MusicBrainzClient
from .providers.discogs import DiscogsClient


@lru_cache
def get_classifier() -> Classifier:
    return Classifier()


@lru_cache
def get_metadata_router() -> MetadataRouter:
    metadata_client = get_metadata_client()
    omdb_client = OMDbClient(api_key=runtime_settings.key_getter("omdb"))
    mb_client = MusicBrainzClient(user_agent=settings.MB_USER_AGENT)
    discogs_client = DiscogsClient(token=runtime_settings.key_getter("discogs"))
    return MetadataRouter(
        metadata_client=metadata_client,
        omdb_client=omdb_client,
        musicbrainz_client=mb_client,
        discogs_client=discogs_client,
    )


__all__ = [
    "Classifier",
    "MetadataRouter",
    "MetadataClient",
    "get_classifier",
    "get_metadata_router",
    "get_metadata_client",
]

