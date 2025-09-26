from collections.abc import Generator
from functools import lru_cache

import redis

from app.core.config import settings


@lru_cache(maxsize=1)
def _redis_client() -> redis.Redis:
    return redis.Redis.from_url(settings.REDIS_URL)


def get_redis() -> Generator[redis.Redis, None, None]:
    client = _redis_client()
    try:
        yield client
    finally:
        pass


__all__ = ["get_redis"]
