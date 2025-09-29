from __future__ import annotations

import hashlib
import json
import os
from typing import Any

import redis.asyncio as redis

from app.core.config import settings

_CACHE_PREFIX = "discovery"
_redis_client: redis.Redis | None = None


def _ensure_client() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.REDIS_URL)
    return _redis_client


def _ttl() -> int:
    raw = os.getenv("DISCOVERY_CACHE_TTL_SECONDS")
    if raw and raw.isdigit():
        return int(raw)
    return int(os.getenv("DISCOVERY_CACHE_TTL", "3600"))


def build_cache_key(provider: str, fn: str, payload: dict[str, Any]) -> str:
    payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    h = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
    return f"{_CACHE_PREFIX}:{provider}:{fn}:{h}"


async def cache_get_json(key: str) -> Any:
    client = _ensure_client()
    raw = await client.get(key)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


async def cache_set_json(key: str, value: Any, ttl: int | None = None) -> None:
    client = _ensure_client()
    payload = json.dumps(value)
    expire = ttl if ttl is not None else _ttl()
    await client.set(key, payload, ex=expire)


async def reset_cache(client: redis.Redis | None = None) -> None:
    global _redis_client
    if client is None:
        client = _redis_client
    if client:
        await client.close()
    _redis_client = None
