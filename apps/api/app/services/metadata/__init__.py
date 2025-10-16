"""Factory helpers for metadata classification and enrichment."""

from __future__ import annotations

from functools import lru_cache

from app.core.config import settings
from app.core.runtime_settings import runtime_settings

from app.services.metadata.classifier import Classifier
from app.services.metadata.metadata_client import (
    MetadataClient,
    get_metadata_client,
)
from app.services.metadata.providers.discogs import DiscogsClient
from app.services.metadata.providers.musicbrainz import MusicBrainzClient
from app.services.metadata.providers.omdb import OMDbClient
from app.services.metadata.router import MetadataRouter


@lru_cache
def get_classifier() -> Classifier:
    return Classifier()


@lru_cache
def get_metadata_router() -> MetadataRouter:
    metadata_client = get_metadata_client()
    omdb_client = OMDbClient(api_key=runtime_settings.key_getter("omdb"))
    mb_client = MusicBrainzClient(
        user_agent=settings.MB_USER_AGENT,
        metadata_client=metadata_client,
    )
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
