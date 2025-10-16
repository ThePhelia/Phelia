"""Configuration for the metadata proxy."""

from __future__ import annotations

from functools import lru_cache

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    tmdb_api_key: str | None = Field(default=None, env="TMDB_API_KEY")
    lastfm_api_key: str | None = Field(default=None, env="LASTFM_API_KEY")
    fanart_api_key: str | None = Field(default=None, env="FANART_API_KEY")

    cache_backend: str = Field(default="sqlite", env="CACHE_BACKEND")
    sqlite_cache_path: str = Field(default="/data/cache.db", env="SQLITE_CACHE_PATH")
    redis_url: str | None = Field(default=None, env="REDIS_URL")

    rate_limit_rps: float = Field(default=5.0, env="RATE_LIMIT_RPS")
    retry_attempts: int = Field(default=3, env="RETRY_ATTEMPTS")
    retry_backoff_base: float = Field(default=0.3, env="RETRY_BACKOFF_BASE")

    tmdb_base_url: AnyHttpUrl = Field("https://api.themoviedb.org/3/", env="TMDB_BASE_URL")
    lastfm_base_url: AnyHttpUrl = Field("https://ws.audioscrobbler.com/2.0/", env="LASTFM_BASE_URL")
    musicbrainz_base_url: AnyHttpUrl = Field(
        "https://musicbrainz.org/ws/2/", env="MUSICBRAINZ_BASE_URL"
    )
    fanart_base_url: AnyHttpUrl = Field("https://webservice.fanart.tv/v3/", env="FANART_BASE_URL")

    mb_user_agent: str = Field(
        "Phelia-Metadata-Proxy/1.0 (+https://example.local)", env="MB_USER_AGENT"
    )

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[arg-type]
