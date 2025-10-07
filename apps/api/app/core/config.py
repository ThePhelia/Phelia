"""Application configuration utilities.

This module centralises all environment driven configuration so that
other parts of the application can rely on a single source of truth.

New metadata pipeline components rely on a variety of third-party
provider API keys.  They are expressed here with sensible defaults so
that the rest of the application can reason about provider
availability without defensive environment checks scattered across the
codebase.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl, ValidationError


class Settings(BaseSettings):
    APP_ENV: str = "dev"
    APP_SECRET: str

    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    DATABASE_URL: str
    REDIS_URL: str

    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str

    BT_CLIENT: str = "qb"
    QB_URL: AnyHttpUrl
    QB_USER: str
    QB_PASS: str

    ALLOWED_SAVE_DIRS: str = "/downloads,/music"
    DEFAULT_SAVE_DIR: str = "/downloads"

    CORS_ORIGINS: str = "*"

    # -------- Metadata / Provider configuration --------
    # TMDb is the primary enrichment provider for movies and TV series.
    # The API key is required for deep enrichment but the application
    # handles a missing key gracefully by returning classification-only
    # results so that the UI can still prompt the user for action.
    TMDB_API_KEY: str | None = None

    # Optional OMDb key.  When provided we can enhance TMDb results
    # with IMDb ratings/Metascore; otherwise the feature is skipped.
    OMDB_API_KEY: str | None = None

    # Optional Discogs token for music metadata.  Discogs allows
    # unauthenticated requests in limited fashion but we keep it
    # configurable to respect the API's expected authentication.
    DISCOGS_TOKEN: str | None = None

    # Optional Last.fm key used to surface listening metrics and tags.
    LASTFM_API_KEY: str | None = None

    # Apple Music RSS storefront used for discovery feeds.
    APPLE_RSS_STOREFRONT: str = "us"

    # Default cache TTL for discovery endpoints (seconds).
    DISCOVERY_CACHE_TTL: int = 86_400

    # MusicBrainz encourages clients to send an informative user agent.
    # We ship a sensible default that complies with their etiquette.
    MB_USER_AGENT: str = "Phelia/0.1 (https://example.local)"

    METADATA_BASE_URL: AnyHttpUrl | None = None

    class Config:
        extra = "ignore"

try:
    settings = Settings()  # type: ignore
except ValidationError as e:
    missing = ", ".join(err["loc"][0] for err in e.errors())
    raise RuntimeError(
        f"Missing required configuration variables: {missing}"
    ) from e

if settings.METADATA_BASE_URL is None:
    raise RuntimeError("METADATA_BASE_URL is required")
