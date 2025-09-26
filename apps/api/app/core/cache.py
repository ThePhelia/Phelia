import json
from typing import Any


def cache_get(client, key: str):
    value = client.get(key)
    if not value:
        return None
    if isinstance(value, bytes):
        value = value.decode("utf-8")
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return None


def cache_set(client, key: str, data: Any, ttl: int) -> None:
    client.set(key, json.dumps(data), ex=ttl)


__all__ = ["cache_get", "cache_set"]
