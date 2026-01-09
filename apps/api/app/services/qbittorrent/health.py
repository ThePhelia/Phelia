r"""Blocking qBittorrent health utilities used during application startup.

Developers running against a local qBittorrent instance can relax ban
thresholds by editing ``qBittorrent.conf`` (mounted volume) with::

    [Preferences]
    WebUI\MaxAuthenticationFailCount=999
    WebUI\BanDuration=0
    WebUI\HostHeaderValidation=false
    ; (optionally) WebUI\AuthSubnetWhitelist=172.18.0.0/16
"""

from __future__ import annotations

import logging
import os
import random
import time
from typing import Final

import httpx

log = logging.getLogger(__name__)

_TIMEOUT_SECONDS: Final[int] = 5
_DEFAULT_TRIES: Final[int] = 12
_BACKOFF_FACTOR: Final[float] = 1.5
_MAX_DELAY: Final[float] = 15.0


def _env(*names: str) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return None


def qb_login_ok() -> bool | None:
    """Attempt to authenticate with qBittorrent using exponential backoff."""

    if os.getenv("QBIT_HEALTHCHECK_DISABLED", "").lower() == "true":
        log.info("qBittorrent health-check disabled by env.")
        return None

    url = (_env("QBIT_URL", "QB_URL") or "http://qbittorrent:8080").rstrip("/")
    user = _env("QBIT_USERNAME", "QB_USER") or "admin"
    pwd = _env("QBIT_PASSWORD", "QB_PASS") or ""

    if not pwd:
        log.warning("qBittorrent health-check skipped: QBIT_PASSWORD is not set.")
        return None

    tries = int(os.getenv("QBIT_HEALTH_TRIES", str(_DEFAULT_TRIES)))
    delay = 1.0
    endpoint = f"{url}/api/v2/auth/login"

    for attempt in range(1, tries + 1):
        try:
            resp = httpx.post(
                endpoint,
                data={"username": user, "password": pwd},
                timeout=_TIMEOUT_SECONDS,
            )
            body = (resp.text or "")[:200]
        except httpx.RequestError as exc:  # pragma: no cover - defensive guard
            log.warning(
                "qBittorrent not reachable (%s) [attempt %d/%d, url=%s, user=%s]",
                exc.__class__.__name__,
                attempt,
                tries,
                url,
                user,
            )
        else:
            cookie_ok = bool(resp.cookies.get("SID") or resp.cookies.get("sid"))
            body_ok = body.strip().lower() in {"ok", "ok.", ""}
            if resp.status_code == 200 and (body_ok or cookie_ok):
                return True

            body_lower = body.lower()
            if resp.status_code == 403 and "banned" in body_lower:
                log.error(
                    "qBittorrent login blocked: IP banned by qBittorrent (attempt %d/%d, url=%s, user=%s)."
                    " Fix credentials or adjust qB WebUI ban settings, then restart.",
                    attempt,
                    tries,
                    url,
                    user,
                )
                return False

            if resp.status_code == 401 or "fails due to bad credentials" in body_lower:
                log.warning(
                    "qBittorrent login rejected (status=%s, body=%r) [attempt %d/%d, url=%s, user=%s]."
                    " Verify QBIT_USERNAME/QBIT_PASSWORD and ensure the API targets the internal URL"
                    " (http://qbittorrent:8080).",
                    resp.status_code,
                    body,
                    attempt,
                    tries,
                    url,
                    user,
                )
            else:
                log.warning(
                    "qBittorrent login not ready (status=%s, body=%r) [attempt %d/%d, url=%s, user=%s]",
                    resp.status_code,
                    body,
                    attempt,
                    tries,
                    url,
                    user,
                )

        if attempt >= tries:
            break

        sleep_for = min(delay, _MAX_DELAY) + random.random() * 0.5
        time.sleep(sleep_for)
        delay = min(delay * _BACKOFF_FACTOR, _MAX_DELAY)

    log.error(
        "qBittorrent health-check failed: login unsuccessful after %d attempts (url=%s, user=%s).",
        tries,
        url,
        user,
    )
    return False
