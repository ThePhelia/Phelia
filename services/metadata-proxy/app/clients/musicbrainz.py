"""MusicBrainz proxy router."""

from __future__ import annotations

from fastapi import APIRouter, Request

from ..config import Settings, get_settings
from ..ratelimit import TokenBucket
from . import ProviderConfig, create_router

MB_TTL = 60 * 60 * 24  # 24 hours


def _mb_params(request: Request, _: str, __: Settings) -> list[tuple[str, str]]:
    if "fmt" in request.query_params:
        return []
    return [("fmt", "json")]


def _mb_headers(_: Request, __: str, settings: Settings) -> dict[str, str]:
    return {"accept": "application/json", "user-agent": settings.mb_user_agent}


_settings = get_settings()
_mb_rate_limiter = TokenBucket(rate=_settings.rate_limit_rps)

router: APIRouter = create_router(
    ProviderConfig(
        name="musicbrainz",
        base_url=str(_settings.musicbrainz_base_url),
        ttl=MB_TTL,
        build_params=_mb_params,
        build_headers=_mb_headers,
    ),
    _mb_rate_limiter,
)
