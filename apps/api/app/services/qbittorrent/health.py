"""Blocking qBittorrent health utilities used during application startup."""

from __future__ import annotations

import logging
import os
import time
from typing import Final

import httpx

log = logging.getLogger(__name__)

_MAX_ATTEMPTS: Final[int] = 25
_SLEEP_SECONDS: Final[int] = 2
_TIMEOUT_SECONDS: Final[int] = 5


def qb_login_ok() -> bool:
    """Attempt to authenticate with qBittorrent using simple retries."""

    url = os.getenv("QBIT_URL", "http://qbittorrent:8080").rstrip("/")
    user = os.getenv("QBIT_USERNAME", "admin")
    pwd = os.getenv("QBIT_PASSWORD", "adminadmin")

    endpoint = f"{url}/api/v2/auth/login"
    for attempt in range(_MAX_ATTEMPTS):
        try:
            resp = httpx.post(
                endpoint,
                data={"username": user, "password": pwd},
                timeout=_TIMEOUT_SECONDS,
            )
        except httpx.RequestError as exc:  # pragma: no cover - defensive guard
            log.warning(
                "qBittorrent not reachable (%s), attempt %d/%d",
                exc.__class__.__name__,
                attempt + 1,
                _MAX_ATTEMPTS,
            )
        else:
            if resp.status_code == 200 and resp.text == "Ok.":
                return True
            log.warning(
                "qBittorrent login not ready (status=%s, body=%r), attempt %d/%d",
                resp.status_code,
                resp.text[:100],
                attempt + 1,
                _MAX_ATTEMPTS,
            )
        time.sleep(_SLEEP_SECONDS)

    log.error("qBittorrent health check failed: Login failed at %s", endpoint)
    return False
