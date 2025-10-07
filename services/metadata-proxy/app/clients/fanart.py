"""Fanart.tv proxy router."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from ..config import get_settings
from ..ratelimit import TokenBucket
from . import ProviderConfig, create_router

FANART_TTL = 60 * 60 * 24 * 7  # 7 days


def _fanart_params(_: Request, __: str, settings) -> list[tuple[str, str]]:
    if not settings.fanart_api_key:
        raise HTTPException(status_code=503, detail="fanart_not_configured")
    return [("api_key", settings.fanart_api_key)]


def _fanart_headers(_: Request, __: str, ___) -> dict[str, str]:
    return {"accept": "application/json"}


_settings = get_settings()
_fanart_rate_limiter = TokenBucket(rate=_settings.rate_limit_rps)

router: APIRouter = create_router(
    ProviderConfig(
        name="fanart",
        base_url=str(_settings.fanart_base_url),
        ttl=FANART_TTL,
        build_params=_fanart_params,
        build_headers=_fanart_headers,
    ),
    _fanart_rate_limiter,
)
