"""TMDB proxy router."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from ..config import get_settings
from ..ratelimit import TokenBucket
from . import ProviderConfig, create_router

TMDB_TTL = 60 * 60 * 12  # 12 hours


def _tmdb_params(_: Request, __: str, settings) -> list[tuple[str, str]]:
    params: list[tuple[str, str]] = []
    if not settings.tmdb_api_key:
        raise HTTPException(status_code=503, detail="tmdb_not_configured")
    params.append(("api_key", settings.tmdb_api_key))
    return params


def _tmdb_headers(request: Request, _: str, __) -> dict[str, str]:
    headers = {"accept": "application/json"}
    language = request.headers.get("accept-language")
    if language:
        headers["accept-language"] = language
    return headers


_settings = get_settings()
_tmdb_rate_limiter = TokenBucket(rate=_settings.rate_limit_rps)

router: APIRouter = create_router(
    ProviderConfig(
        name="tmdb",
        base_url=str(_settings.tmdb_base_url),
        ttl=TMDB_TTL,
        build_params=_tmdb_params,
        build_headers=_tmdb_headers,
    ),
    _tmdb_rate_limiter,
)
