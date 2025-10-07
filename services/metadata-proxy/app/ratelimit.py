"""Rate limiting primitives used by the metadata proxy."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass


@dataclass
class TokenBucket:
    """Simple token bucket rate limiter supporting awaitable acquire."""

    rate: float
    capacity: float | None = None

    def __post_init__(self) -> None:
        self.capacity = self.capacity or self.rate
        self._tokens = float(self.capacity)
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        while True:
            async with self._lock:
                now = time.monotonic()
                elapsed = now - self._last_refill
                self._last_refill = now
                self._tokens = min(
                    self.capacity or self.rate, self._tokens + elapsed * self.rate
                )
                if self._tokens >= 1:
                    self._tokens -= 1
                    return
                wait_time = (1 - self._tokens) / self.rate if self.rate > 0 else 0
            await asyncio.sleep(max(0.0, wait_time))
