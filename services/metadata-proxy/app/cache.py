"""Caching utilities for the metadata proxy."""

from __future__ import annotations

import asyncio
import sqlite3
import time
from abc import ABC, abstractmethod
from pathlib import Path

try:  # pragma: no cover - optional dependency
    import redis.asyncio as redis
except ImportError:  # pragma: no cover - fallback for legacy aioredis package
    redis = None  # type: ignore

from .config import Settings


class CacheBackend(ABC):
    """Abstract cache interface."""

    @abstractmethod
    async def get(self, key: str) -> bytes | None:
        raise NotImplementedError

    @abstractmethod
    async def set(self, key: str, value: bytes, ttl: int) -> None:
        raise NotImplementedError

    async def close(self) -> None:  # pragma: no cover - optional override
        return None


class MemoryCache(CacheBackend):
    """Simple in-memory cache suitable for development."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[float, bytes]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> bytes | None:
        async with self._lock:
            entry = self._store.get(key)
            if not entry:
                return None
            expires_at, payload = entry
            if expires_at and expires_at < time.monotonic():
                self._store.pop(key, None)
                return None
            return payload

    async def set(self, key: str, value: bytes, ttl: int) -> None:
        async with self._lock:
            expires_at = time.monotonic() + ttl if ttl else 0
            self._store[key] = (expires_at, value)


class SQLiteCache(CacheBackend):
    """SQLite-backed cache for lightweight deployments."""

    def __init__(self, path: str) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._path, check_same_thread=False)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cache (
                key TEXT PRIMARY KEY,
                value BLOB NOT NULL,
                expires_at REAL NOT NULL
            )
            """
        )
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_cache_exp ON cache (expires_at)")
        self._conn.commit()
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> bytes | None:
        async with self._lock:
            now = time.time()
            cursor = self._conn.execute(
                "SELECT value, expires_at FROM cache WHERE key = ?", (key,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            value, expires_at = row
            if expires_at and expires_at < now:
                self._conn.execute("DELETE FROM cache WHERE key = ?", (key,))
                self._conn.commit()
                return None
            return value

    async def set(self, key: str, value: bytes, ttl: int) -> None:
        async with self._lock:
            expires_at = time.time() + ttl if ttl else time.time()
            self._conn.execute(
                "REPLACE INTO cache (key, value, expires_at) VALUES (?, ?, ?)",
                (key, value, expires_at),
            )
            self._conn.commit()

    async def close(self) -> None:
        self._conn.close()


class RedisCache(CacheBackend):
    """Redis-backed cache leveraging redis-py asyncio support."""

    def __init__(self, url: str) -> None:
        if not redis:  # pragma: no cover - defensive
            raise RuntimeError("redis dependency not available")
        self._client = redis.from_url(url, encoding="utf-8", decode_responses=False)

    async def get(self, key: str) -> bytes | None:
        value = await self._client.get(key)
        if value is None:
            return None
        return value if isinstance(value, (bytes, bytearray)) else bytes(value)

    async def set(self, key: str, value: bytes, ttl: int) -> None:
        await self._client.set(name=key, value=value, ex=ttl or None)

    async def close(self) -> None:
        await self._client.close()


_cache_backend: CacheBackend | None = None


async def init_cache(settings: Settings) -> CacheBackend:
    global _cache_backend
    if _cache_backend is not None:
        return _cache_backend

    backend = settings.cache_backend.lower()
    if backend == "memory":
        _cache_backend = MemoryCache()
    elif backend == "redis":
        if not settings.redis_url:
            raise RuntimeError("REDIS_URL must be set when CACHE_BACKEND=redis")
        _cache_backend = RedisCache(settings.redis_url)
    else:
        _cache_backend = SQLiteCache(settings.sqlite_cache_path)
    return _cache_backend


def get_cache() -> CacheBackend:
    if _cache_backend is None:
        raise RuntimeError("Cache backend not initialised")
    return _cache_backend


async def close_cache() -> None:
    if _cache_backend is not None:
        await _cache_backend.close()
