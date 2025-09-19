"""Factory helpers for metadata classification and enrichment."""

from __future__ import annotations

from functools import lru_cache

from app.core.config import settings

from .classifier import Classifier
from .router import MetadataRouter
from .providers.tmdb import TMDBClient
from .providers.omdb import OMDbClient
from .providers.musicbrainz import MusicBrainzClient
from .providers.discogs import DiscogsClient
from .providers.lastfm import LastFMClient


@lru_cache
def get_classifier() -> Classifier:
    return Classifier()


@lru_cache
def get_metadata_router() -> MetadataRouter:
    tmdb_client = TMDBClient(api_key=settings.TMDB_API_KEY)
    omdb_client = OMDbClient(api_key=settings.OMDB_API_KEY)
    mb_client = MusicBrainzClient(user_agent=settings.MB_USER_AGENT)
    discogs_client = DiscogsClient(token=settings.DISCOGS_TOKEN)
    lastfm_client = LastFMClient(api_key=settings.LASTFM_API_KEY)
    return MetadataRouter(
        tmdb_client=tmdb_client,
        omdb_client=omdb_client,
        musicbrainz_client=mb_client,
        discogs_client=discogs_client,
        lastfm_client=lastfm_client,
    )

