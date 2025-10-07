"""Common provider routing helpers."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Iterable, Mapping
from urllib.parse import urlencode, urljoin

import httpx
import orjson
from fastapi import APIRouter, HTTPException, Request

from ..cache import CacheBackend, get_cache
from ..config import Settings, get_settings
from ..http import request_json
from ..ratelimit import TokenBucket
from ..schemas import ProxyPayload

logger = logging.getLogger(__name__)

ParamBuilder = Callable[[Request, str, Settings], list[tuple[str, str]]]
HeaderBuilder = Callable[[Request, str, Settings], Mapping[str, str]]


@dataclass
class ProviderConfig:
    name: str
    base_url: str
    ttl: int
    build_params: ParamBuilder
    build_headers: HeaderBuilder


def _default_headers(_: Request, __: str, ___: Settings) -> Mapping[str, str]:
    return {"accept": "application/json"}


def _cache_key(url: str, params: Iterable[tuple[str, str]]) -> str:
    encoded = urlencode(sorted(params)) if params else ""
    return f"{url}?{encoded}" if encoded else url


async def _ensure_cache() -> CacheBackend:
    return get_cache()


async def proxy_request(
    request: Request,
    path: str,
    config: ProviderConfig,
    *,
    rate_limiter: TokenBucket,
    settings: Settings,
) -> ProxyPayload:
    await rate_limiter.acquire()

    upstream_url = urljoin(str(config.base_url), path)
    query_items = list(request.query_params.multi_items())
    extra_params = config.build_params(request, path, settings)
    params = query_items + extra_params
    cache_key = _cache_key(upstream_url, params)

    cache = await _ensure_cache()
    cached_blob = await cache.get(cache_key)
    if cached_blob:
        cached_payload = orjson.loads(cached_blob)
        data = cached_payload["data"]
        fetched_at = datetime.fromisoformat(cached_payload["fetched_at"])  # type: ignore[arg-type]
        logger.info(
            json.dumps(
                {
                    "event": "proxy_fetch",
                    "provider": config.name,
                    "status": 200,
                    "cached": True,
                    "latency_ms": 0,
                    "request_id": request.headers.get("x-request-id"),
                    "endpoint": path,
                }
            )
        )
        return ProxyPayload(
            provider=config.name,
            cached=True,
            fetched_at=fetched_at,
            data=_attach_metadata(data, config.name, True, fetched_at),
        )

    headers = dict(config.build_headers(request, path, settings))
    request_id = request.headers.get("x-request-id")
    if request_id:
        headers.setdefault("x-request-id", request_id)

    start = time.perf_counter()
    response = await request_json(
        "GET", upstream_url, params=httpx.QueryParams(params), headers=headers
    )
    latency = time.perf_counter() - start

    if response.status_code >= 400:
        message = response.text
        logger.warning(
            json.dumps(
                {
                    "event": "proxy_error",
                    "provider": config.name,
                    "status": response.status_code,
                    "request_id": request_id,
                    "latency_ms": round(latency * 1000, 2),
                }
            )
        )
        raise HTTPException(
            status_code=response.status_code,
            detail={
                "error": "upstream_error",
                "status": response.status_code,
                "upstream_status": response.status_code,
                "request_id": request_id,
                "message": message,
            },
        )

    fetched_at = datetime.now(timezone.utc)
    payload = response.json()
    body = _attach_metadata(payload, config.name, False, fetched_at)

    cache_control = response.headers.get("cache-control", "").lower()
    if "no-store" not in cache_control:
        stored = orjson.dumps({"data": payload, "fetched_at": fetched_at.isoformat()})
        await cache.set(cache_key, stored, config.ttl)

    logger.info(
        json.dumps(
            {
                "event": "proxy_fetch",
                "provider": config.name,
                "status": response.status_code,
                "cached": False,
                "latency_ms": round(latency * 1000, 2),
                "request_id": request_id,
                "endpoint": path,
            }
        )
    )

    return ProxyPayload(provider=config.name, cached=False, fetched_at=fetched_at, data=body)


def _attach_metadata(data: object, provider: str, cached: bool, fetched_at: datetime) -> object:
    if isinstance(data, dict):
        data = dict(data)
        data.setdefault("provider", provider)
        data.setdefault("cached", cached)
        data.setdefault("fetched_at", fetched_at.isoformat())
        return data
    return {
        "provider": provider,
        "cached": cached,
        "fetched_at": fetched_at.isoformat(),
        "data": data,
    }


def create_router(config: ProviderConfig, rate_limiter: TokenBucket) -> APIRouter:
    router = APIRouter()

    settings = get_settings()

    @router.get("/{path:path}")
    async def handler(path: str, request: Request) -> object:
        payload = await proxy_request(
            request,
            path,
            config,
            rate_limiter=rate_limiter,
            settings=settings,
        )
        return payload.data

    return router
