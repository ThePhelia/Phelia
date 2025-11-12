"""HTTP client helpers."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Mapping

import httpx

try:  # pragma: no cover - optional dependency during runtime
    from tenacity import (  # type: ignore[import-untyped]
        AsyncRetrying,
        RetryError,
        retry_if_exception_type,
        stop_after_attempt,
        wait_exponential,
    )
except ModuleNotFoundError:  # pragma: no cover - fallback when tenacity unavailable
    AsyncRetrying = None  # type: ignore[assignment]
    RetryError = Exception  # type: ignore[assignment]
    retry_if_exception_type = stop_after_attempt = wait_exponential = None  # type: ignore[assignment]

from .config import get_settings

logger = logging.getLogger(__name__)

_client: httpx.AsyncClient | None = None


class UpstreamRetryError(Exception):
    """Raised when an upstream response should trigger a retry."""

    def __init__(self, response: httpx.Response) -> None:
        self.response = response
        super().__init__(f"upstream status {response.status_code}")


async def get_http_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=5.0, read=10.0, write=10.0),
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
        )
    return _client


async def close_http_client() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


async def request_json(
    method: str,
    url: str,
    *,
    params: Mapping[str, Any] | None = None,
    headers: Mapping[str, str] | None = None,
) -> httpx.Response:
    """Perform an HTTP request with retry semantics."""

    client = await get_http_client()
    settings = get_settings()

    async def _send() -> httpx.Response:
        response = await client.request(method, url, params=params, headers=headers)
        if response.status_code in {429} or 500 <= response.status_code < 600:
            raise UpstreamRetryError(response)
        return response

    if AsyncRetrying is None:
        attempts = max(1, settings.retry_attempts)
        for attempt in range(1, attempts + 1):
            try:
                response = await _send()
                return response
            except UpstreamRetryError as exc:
                if attempt == attempts:
                    return exc.response
                backoff = settings.retry_backoff_base * (2 ** (attempt - 1))
                await asyncio.sleep(backoff)
            except httpx.RequestError as exc:
                if attempt == attempts:
                    logger.warning("request error url=%s error=%s", url, exc)
                    raise
                backoff = settings.retry_backoff_base * (2 ** (attempt - 1))
                await asyncio.sleep(backoff)
        raise RuntimeError("Unreachable retry loop")  # pragma: no cover - safety

    retry = AsyncRetrying(
        reraise=True,
        stop=stop_after_attempt(settings.retry_attempts),
        wait=wait_exponential(multiplier=settings.retry_backoff_base, min=0.3, max=5),
        retry=retry_if_exception_type(
            (httpx.RequestError, UpstreamRetryError, httpx.HTTPStatusError)
        ),
    )

    try:
        async for attempt in retry:
            with attempt:
                response = await _send()
    except RetryError as exc:  # pragma: no cover - defensive
        last_attempt = exc.last_attempt
        if last_attempt and isinstance(
            last_attempt.outcome.exception(), UpstreamRetryError
        ):
            return last_attempt.outcome.exception().response  # type: ignore[return-value]
        raise
    except UpstreamRetryError as exc:
        return exc.response
    except httpx.RequestError as exc:  # pragma: no cover - network issues
        logger.warning("request error url=%s error=%s", url, exc)
        raise
    else:
        return response
