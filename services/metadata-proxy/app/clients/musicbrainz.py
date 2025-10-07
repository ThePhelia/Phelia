"""MusicBrainz proxy router."""

from __future__ import annotations

from fastapi import APIRouter, Request

from ..config import get_settings
from ..ratelimit import TokenBucket
from . import ProviderConfig, create_router

MB_TTL = 60 * 60 * 24  # 24 hours


def _mb_params(request: Request, _: str, __) -> list[tuple[str, str]]:
    params = list(request.query_params.multi_items())
    if not any(key == "fmt" for key, _ in params):
        params.append(("fmt", "json"))
    return params


def _mb_headers(_: Request, __: str, settings) -> dict[str, str]:
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
