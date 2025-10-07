"""Last.fm proxy router."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from ..config import get_settings
from ..ratelimit import TokenBucket
from . import ProviderConfig, create_router

LASTFM_TTL = 60 * 60 * 24  # 24 hours


def _lastfm_params(request: Request, path: str, settings) -> list[tuple[str, str]]:
    if not settings.lastfm_api_key:
        raise HTTPException(status_code=503, detail="lastfm_not_configured")
    params = [("api_key", settings.lastfm_api_key), ("format", "json")]
    if path and "method" not in request.query_params:
        params.append(("method", path))
    return params


def _lastfm_headers(_: Request, __: str, ___) -> dict[str, str]:
    return {"accept": "application/json"}


_settings = get_settings()
_lastfm_rate_limiter = TokenBucket(rate=_settings.rate_limit_rps)

router: APIRouter = create_router(
    ProviderConfig(
        name="lastfm",
        base_url=str(_settings.lastfm_base_url),
        ttl=LASTFM_TTL,
        build_params=_lastfm_params,
        build_headers=_lastfm_headers,
    ),
    _lastfm_rate_limiter,
)
